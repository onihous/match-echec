"""
Jeu d'échecs en ligne - Version 1
Backend : Flask + Flask-SocketIO + python-chess
Le serveur est la seule source de vérité sur l'état de la partie.
"""

import re
import chess
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

# ============================================================
# Configuration de l'application
# ============================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'match-echec-secret-v1'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# ============================================================
# État global du jeu (source de vérité unique, en mémoire)
# ============================================================

board = chess.Board()
connected_users = {}          # sid -> {"name": str}
captured_pieces = {            # pièces capturées, classées par camp d'origine
    "white": [],               # pièces blanches qui ont été prises
    "black": []                # pièces noires qui ont été prises
}
edit_mode = False              # True = plateau en mode édition libre

# Valeur des pièces (barème standard)
PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0
}

# Symboles Unicode des pièces pour l'affichage des captures
PIECE_UNICODE = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
}


# ============================================================
# Fonctions utilitaires
# ============================================================

def get_game_state():
    """
    Retourne l'état complet du jeu pour envoi aux clients.
    C'est cette fonction qui fait foi pour tout le monde.
    """
    # Déterminer le statut de la partie
    status = "playing"
    if edit_mode:
        status = "editing"
    elif board.is_checkmate():
        winner = "Noirs" if board.turn == chess.WHITE else "Blancs"
        status = f"checkmate:{winner}"
    elif board.is_stalemate():
        status = "stalemate"
    elif board.is_insufficient_material():
        status = "insufficient"
    elif board.is_check():
        status = "check"

    # Calculer les coups légaux, groupés par case de départ
    legal_moves = {}
    if not edit_mode and status in ("playing", "check"):
        for move in board.legal_moves:
            from_sq = chess.square_name(move.from_square)
            to_sq = chess.square_name(move.to_square)
            if from_sq not in legal_moves:
                legal_moves[from_sq] = []
            # Éviter les doublons (promotions multiples sur la même case)
            if to_sq not in legal_moves[from_sq]:
                legal_moves[from_sq].append(to_sq)

    # Case du roi en échec (pour la mise en surbrillance)
    king_in_check = None
    if board.is_check():
        king_square = board.king(board.turn)
        if king_square is not None:
            king_in_check = chess.square_name(king_square)

    return {
        "fen": board.fen(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "status": status,
        "legal_moves": legal_moves,
        "captured": captured_pieces,
        "edit_mode": edit_mode,
        "king_in_check": king_in_check,
        "users": {sid: data["name"] for sid, data in connected_users.items()}
    }


def make_unique_name(name):
    """Ajoute un suffixe numérique si le prénom est déjà utilisé."""
    existing_names = [u["name"] for u in connected_users.values()]
    if name not in existing_names:
        return name
    suffix = 2
    while f"{name} ({suffix})" in existing_names:
        suffix += 1
    return f"{name} ({suffix})"


def reset_game():
    """Remet la partie à zéro (position initiale)."""
    global board, captured_pieces, edit_mode
    board = chess.Board()
    captured_pieces = {"white": [], "black": []}
    edit_mode = False


def clear_board_for_editing():
    """Vide le plateau et passe en mode édition."""
    global board, captured_pieces, edit_mode
    board.clear()
    captured_pieces = {"white": [], "black": []}
    edit_mode = True


# ============================================================
# Route HTTP principale
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')


# ============================================================
# Événements WebSocket
# ============================================================

@socketio.on('connect')
def handle_connect():
    """Connexion brute — on attend le 'join' avec le prénom."""
    pass


@socketio.on('join')
def handle_join(data):
    """Un joueur indique son prénom et rejoint la partie."""
    name = data.get('name', '').strip()

    # --- Validation du prénom ---
    if not name:
        emit('error', {'message': 'Le prénom ne peut pas être vide.'})
        return
    if len(name) > 20:
        emit('error', {'message': 'Le prénom ne doit pas dépasser 20 caractères.'})
        return
    if not re.match(r'^[a-zA-ZÀ-ÿ0-9 \-]+$', name):
        emit('error', {'message': 'Caractères spéciaux non autorisés.'})
        return

    unique_name = make_unique_name(name)
    connected_users[request.sid] = {"name": unique_name}

    # Envoyer confirmation + état complet au nouveau joueur
    emit('joined', {'name': unique_name, 'sid': request.sid})
    emit('game_state', get_game_state())

    # Informer tous les autres
    emit('user_joined', {
        'name': unique_name, 'sid': request.sid
    }, broadcast=True, include_self=False)

    # Mettre à jour la liste pour tout le monde
    emit('users_list', {
        sid: u["name"] for sid, u in connected_users.items()
    }, broadcast=True)


@socketio.on('disconnect')
def handle_disconnect():
    """Un joueur se déconnecte ou perd la connexion."""
    user = connected_users.pop(request.sid, None)
    if user:
        emit('user_left', {
            'name': user["name"], 'sid': request.sid
        }, broadcast=True)
        emit('users_list', {
            sid: u["name"] for sid, u in connected_users.items()
        }, broadcast=True)


@socketio.on('attempt_move')
def handle_attempt_move(data):
    """
    Le client propose un déplacement.
    Le serveur vérifie la légalité et l'applique (ou le refuse).
    """
    if edit_mode:
        emit('error', {'message': 'Le plateau est en mode édition.'})
        return

    if board.is_game_over():
        emit('error', {'message': 'La partie est terminée. Cliquez sur Réinitialiser.'})
        return

    from_sq = data.get('from', '')
    to_sq = data.get('to', '')
    promotion = data.get('promotion')

    try:
        from_square = chess.parse_square(from_sq)
        to_square = chess.parse_square(to_sq)
    except ValueError:
        emit('error', {'message': 'Case invalide.'})
        return

    # Vérifier si c'est une promotion de pion
    piece = board.piece_at(from_square)
    if piece and piece.piece_type == chess.PAWN:
        target_rank = chess.square_rank(to_square)
        is_promotion = (piece.color == chess.WHITE and target_rank == 7) or \
                       (piece.color == chess.BLACK and target_rank == 0)
        if is_promotion and not promotion:
            # Demander au client de choisir la pièce de promotion
            emit('promotion_needed', {'from': from_sq, 'to': to_sq})
            return

    # Construire l'objet Move
    if promotion:
        promo_map = {
            'queen': chess.QUEEN,
            'rook': chess.ROOK,
            'bishop': chess.BISHOP,
            'knight': chess.KNIGHT
        }
        promo_piece = promo_map.get(promotion, chess.QUEEN)
        move = chess.Move(from_square, to_square, promotion=promo_piece)
    else:
        move = chess.Move(from_square, to_square)

    # Vérification de légalité
    if move not in board.legal_moves:
        emit('error', {'message': 'Coup illégal.'})
        return

    # --- Le coup est valide : on l'applique ---

    # Détecter une capture
    captured = board.piece_at(to_square)
    is_en_passant = board.is_en_passant(move)
    if is_en_passant:
        captured = chess.Piece(chess.PAWN, not board.turn)

    was_capture = captured is not None

    if captured:
        color_key = "white" if captured.color == chess.WHITE else "black"
        captured_pieces[color_key].append({
            "symbol": captured.symbol(),
            "value": PIECE_VALUES.get(captured.piece_type, 0)
        })

    # Jouer le coup sur le plateau officiel
    board.push(move)

    # Nom du joueur qui a joué
    player_name = connected_users.get(request.sid, {}).get("name", "Inconnu")

    # Diffuser le nouvel état à tout le monde
    state = get_game_state()
    state["last_move"] = {"from": from_sq, "to": to_sq, "player": player_name, "was_capture": was_capture}
    emit('game_state', state, broadcast=True)


@socketio.on('reset')
def handle_reset():
    """Réinitialiser le plateau (position de départ)."""
    reset_game()
    player_name = connected_users.get(request.sid, {}).get("name", "Inconnu")
    state = get_game_state()
    state["reset_by"] = player_name
    emit('game_state', state, broadcast=True)


@socketio.on('clear_board')
def handle_clear():
    """Vider le plateau et passer en mode édition."""
    clear_board_for_editing()
    emit('game_state', get_game_state(), broadcast=True)


@socketio.on('edit_place_piece')
def handle_edit_place(data):
    """Placer ou retirer une pièce en mode édition."""
    if not edit_mode:
        emit('error', {'message': "Pas en mode édition."})
        return

    square_name = data.get('square', '')
    piece_symbol = data.get('piece')  # ex: 'P', 'p', 'R', 'r'... ou None pour retirer

    try:
        square = chess.parse_square(square_name)
        if piece_symbol:
            piece = chess.Piece.from_symbol(piece_symbol)
            board.set_piece_at(square, piece)
        else:
            board.remove_piece_at(square)
        emit('game_state', get_game_state(), broadcast=True)
    except (ValueError, KeyError):
        emit('error', {'message': 'Pièce ou case invalide.'})


@socketio.on('validate_position')
def handle_validate():
    """Valider la position personnalisée et reprendre le jeu."""
    global edit_mode

    if not edit_mode:
        emit('error', {'message': "Pas en mode édition."})
        return

    # --- Vérifications ---
    white_kings = 0
    black_kings = 0
    pawn_on_edge = False

    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            if piece.piece_type == chess.KING:
                if piece.color == chess.WHITE:
                    white_kings += 1
                else:
                    black_kings += 1
            if piece.piece_type == chess.PAWN:
                rank = chess.square_rank(square)
                if rank == 0 or rank == 7:
                    pawn_on_edge = True

    if white_kings != 1:
        emit('error', {'message': 'Il faut exactement 1 roi blanc.'})
        return
    if black_kings != 1:
        emit('error', {'message': 'Il faut exactement 1 roi noir.'})
        return
    if pawn_on_edge:
        emit('error', {'message': 'Aucun pion ne peut être en rangée 1 ou 8.'})
        return

    # Désactiver les droits de roque, trait aux blancs
    board.set_castling_fen('-')
    board.turn = chess.WHITE
    board.halfmove_clock = 0
    board.fullmove_number = 1

    # Vérifier la validité globale (ex: roi adverse pas en échec)
    if not board.is_valid():
        emit('error', {'message': 'Position invalide (le roi adverse est peut-être en échec).'})
        return

    edit_mode = False
    emit('game_state', get_game_state(), broadcast=True)


@socketio.on('cursor_move')
def handle_cursor(data):
    """Transmettre la position du curseur aux autres joueurs."""
    if request.sid not in connected_users:
        return

    emit('cursor_update', {
        'sid': request.sid,
        'name': connected_users[request.sid]["name"],
        'x': data.get('x', 0),
        'y': data.get('y', 0)
    }, broadcast=True, include_self=False)


# ============================================================
# Point d'entrée
# ============================================================

if __name__ == '__main__':
    print("=== Jeu d'échecs - Version 1 ===")
    print("Ouvrez http://localhost:5000 dans votre navigateur")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
