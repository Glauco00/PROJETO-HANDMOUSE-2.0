import base64
import cv2
import mediapipe as mp
import pyautogui
import time
import threading
import collections
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

pyautogui.FAILSAFE = False

mp_hands = mp.solutions.hands
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7, min_tracking_confidence=0.7)
mp_draw = mp.solutions.drawing_utils

screen_width, screen_height = pyautogui.size()

cap = None
is_running = False
camera_thread = None
handmouse_active = False
click_threshold = 0.05  # Ajustado para maior precisão
selection_active = False
selection_start_time = None

# Suavização do cursor
cursor_positions = collections.deque(maxlen=8)  # Armazena as últimas 8 posições do cursor
last_cursor_position = None

# Fator de escala para ajustar a sensibilidade do cursor
sensitivity_factor = 1.5  # Aumenta a sensibilidade para 150%

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('start_capture')
def start_capture():
    global cap, is_running, camera_thread
    if not is_running:
        cap = cv2.VideoCapture(0)
        is_running = True

        def process_camera():
            global cap, is_running, handmouse_active, selection_active, selection_start_time, cursor_positions, last_cursor_position
            left_click_active = False
            right_click_active = False
            while is_running and cap.isOpened():
                success, frame = cap.read()
                if not success:
                    emit('status', {'message': 'Erro ao acessar a câmera.'}, broadcast=True)
                    break

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = hands.process(frame_rgb)

                if results.multi_hand_landmarks:
                    for hand_landmarks in results.multi_hand_landmarks:
                        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                        if handmouse_active:
                            # Use sempre os TIPs (unha) para máxima precisão
                            thumb_tip = hand_landmarks.landmark[mp_hands.HandLandmark.THUMB_TIP]
                            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
                            middle_tip = hand_landmarks.landmark[mp_hands.HandLandmark.MIDDLE_FINGER_TIP]

                            x = int(index_tip.x * screen_width * sensitivity_factor)
                            y = int(index_tip.y * screen_height * sensitivity_factor)
                            x = screen_width - x

                            cursor_positions.append((x, y))
                            avg_x = int(sum(pos[0] for pos in cursor_positions) / len(cursor_positions))
                            avg_y = int(sum(pos[1] for pos in cursor_positions) / len(cursor_positions))
                            pyautogui.moveTo(avg_x, avg_y)
                            last_cursor_position = (avg_x, avg_y)

                            # Distâncias entre os TIPs
                            dist_index_thumb = ((index_tip.x - thumb_tip.x) ** 2 + (index_tip.y - thumb_tip.y) ** 2) ** 0.5
                            dist_middle_thumb = ((middle_tip.x - thumb_tip.x) ** 2 + (middle_tip.y - thumb_tip.y) ** 2) ** 0.5

                            # Clique esquerdo: indicador + polegar (TIP)
                            if dist_index_thumb < click_threshold and not left_click_active and not selection_active:
                                pyautogui.click()
                                left_click_active = True
                            elif dist_index_thumb >= click_threshold:
                                left_click_active = False

                            # Clique direito: médio + polegar (TIP)
                            if dist_middle_thumb < click_threshold and not right_click_active and not selection_active:
                                pyautogui.click(button='right')
                                right_click_active = True
                            elif dist_middle_thumb >= click_threshold:
                                right_click_active = False

                            # Seleção: indicador + polegar (TIP) juntos por 3s
                            now = time.time()
                            if dist_index_thumb < click_threshold:
                                if not selection_active:
                                    if selection_start_time is None:
                                        selection_start_time = now
                                    elif now - selection_start_time >= 3:
                                        selection_active = True
                                        pyautogui.mouseDown()
                                else:
                                    pyautogui.moveTo(avg_x, avg_y)
                            else:
                                if selection_active:
                                    selection_active = False
                                    selection_start_time = None
                                    pyautogui.mouseUp()
                                else:
                                    selection_start_time = None

                _, buffer = cv2.imencode('.jpg', frame)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                socketio.emit('camera_frame', {'frame': frame_base64})

                time.sleep(0.01)

            if cap:
                cap.release()
            cv2.destroyAllWindows()

        camera_thread = threading.Thread(target=process_camera)
        camera_thread.start()

@socketio.on('stop_capture')
def stop_capture():
    global is_running
    is_running = False

@socketio.on('start_handmouse')
def start_handmouse():
    global handmouse_active
    handmouse_active = True
    emit('status', {'message': 'Controle do HandMouse ativado.'}, broadcast=True)

@socketio.on('stop_handmouse')
def stop_handmouse():
    global handmouse_active
    handmouse_active = False
    emit('status', {'message': 'HandMouse desativado.'}, broadcast=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)