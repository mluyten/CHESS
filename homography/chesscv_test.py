from ChessCV import CCV
import cv2
import game_flow.game as gfg

CV = CCV(square_width=17, board_size=7, cam_height=480, cam_width=640, fps=60, webcam=False, draw_info=False,
         input_video="../test_videos/480_Aruco_Board.mp4",
         chess_icons="../assets/chess_pieces.png")

param = [None]
window_name = 'C.H.E.S.S.'
cv2.namedWindow(window_name)
cv2.setMouseCallback(window_name, CV.click, param)

game = gfg.Game()

while CV.got_video:
    Mext = CV.next_frame()
    if Mext is not None:
        CV.draw_spaces_and_origin(Mext)

        #get board state
        # board = game.getGameState()
        #print board state
        # print(board)

        gameEnded = game.playGame()

        if (gameEnded):
            break

        #get user input
        #print(param)
        if param[-1] is not None:
            cv2.putText(CV.bgr_display, text=param[-1], org=(10, 470),
                        # Displays name of clicked square at bottom right of screen
                        fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                        fontScale=1, color=(255, 0, 255), thickness=2)
            if game.players[game.currentPlayer] == game.Human:
                if not game.Human.haveSelectedFromPiece:
                    game.Human.selectedSquare = param[-1]
                    game.Human.haveSelectedFromPiece = True
                elif (not game.Human.haveSelectedToPiece) and game.Human.haveDeterminedMoves:
                    game.Human.selectedSquare = param[-1]
                    game.Human.haveSelectedToPiece = True

            param.pop()

    else:
        pass
        # CV.outer_corners = None
        # cv2.putText(CV.bgr_display, text="Chessboard/ArUco Not Found", org=(10, 470),
        #             fontFace=cv2.FONT_HERSHEY_SIMPLEX,
        #             fontScale=1, color=(255, 0, 255), thickness=2)

    CV.show_image(window_name=window_name, board_state=game.getGameState())
    key_press = cv2.waitKey(int(1000 / CV.fps))
    if key_press == 27:
        break
