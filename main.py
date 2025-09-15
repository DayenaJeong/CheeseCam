import cv2
import time
from datetime import datetime

# OS별 권장 백엔드 후보
BACKENDS = [
    cv2.CAP_AVFOUNDATION,  # macOS
    cv2.CAP_V4L2,          # Linux
    cv2.CAP_DSHOW,         # Windows
    cv2.CAP_ANY
]

def open_camera():
    # 여러 index / backend 조합으로 카메라 열기
    for idx in [0, 1, 2, 3]:
        for be in BACKENDS:
            cap = cv2.VideoCapture(idx, be)
            if cap.isOpened():
                ok, _ = cap.read()
                if ok:
                    print(f"camera opened: index={idx}, backend={be}")
                    return cap
            cap.release()
    return None

def timestamp_name(ext):
    # ex: record_20250915_142030.avi
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"record_{ts}.{ext}"

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def apply_brightness_contrast(img, brightness=0, contrast=0):
    # brightness: -100~100, contrast: -100~100
    # 간단한 선형 변환: out = img*alpha + beta
    # contrast -> alpha, brightness -> beta
    alpha = 1.0 + (contrast / 100.0)  # 0~2
    beta = brightness                 # -100~100
    out = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    return out

def main():
    cap = open_camera()
    if cap is None:
        print("camera open failed (check device/permissions)")
        return

    # 희망 해상도/FPS (장치가 무시할 수 있음)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    win = "CheeseCam"
    cv2.namedWindow(win)

    # Trackbars for extra feature
    cv2.createTrackbar("Brightness", win, 0, 200, lambda v: None)  # 0~200 -> -100~100
    cv2.setTrackbarPos("Brightness", win, 100)
    cv2.createTrackbar("Contrast", win, 100, 200, lambda v: None)  # 0~200 -> -100~100

    # 상태
    recording = False
    writer = None
    flip_h = False

    # 코덱/컨테이너 토글
    codecs = [("XVID", "avi"), ("mp4v", "mp4")]   # FourCC, ext
    codec_idx = 0

    print("CheeseCam")
    print("Space: start/stop recording   ESC: quit")
    print("f: flip horizontal            c: change codec (XVID<->MP4V)")

    while True:
        ok, frame = cap.read()
        if not ok:
            # 일부 장치에서 간헐적 실패가 있어 skip
            time.sleep(0.01)
            continue

        # flip 옵션
        if flip_h:
            frame = cv2.flip(frame, 1)

        # 트랙바 값 읽기
        b_raw = cv2.getTrackbarPos("Brightness", win)  # 0~200
        c_raw = cv2.getTrackbarPos("Contrast", win)    # 0~200
        brightness = b_raw - 100
        contrast = c_raw - 100
        frame_show = apply_brightness_contrast(frame, brightness, contrast)

        # 녹화
        if recording:
            if writer is None:
                h, w = frame.shape[:2]
                fourcc_str, ext = codecs[codec_idx]
                fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
                filename = timestamp_name(ext)
                writer = cv2.VideoWriter(filename, fourcc, 20.0, (w, h))
                if not writer.isOpened():
                    print("writer open failed")
                    recording = False
                else:
                    print(f"record start -> {filename} ({fourcc_str})")

            if writer is not None:
                writer.write(frame_show)

            # 빨간 점 + 텍스트
            cv2.circle(frame_show, (30, 40), 10, (0, 0, 255), -1)
            cv2.putText(frame_show, "REC", (50, 47),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)

        # 프리뷰
        cv2.imshow(win, frame_show)

        k = cv2.waitKey(1) & 0xFF
        if k == 27:  # ESC
            break
        elif k == 32:  # Space
            recording = not recording
            if not recording:
                if writer is not None:
                    writer.release()
                    writer = None
                print("record stop")
        elif k == ord('f'):
            flip_h = not flip_h
            print(f"flip horizontal: {flip_h}")
        elif k == ord('c'):
            codec_idx = (codec_idx + 1) % len(codecs)
            print(f"codec -> {codecs[codec_idx][0]} .{codecs[codec_idx][1]}")

    cap.release()
    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
