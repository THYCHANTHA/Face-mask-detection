import os
from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
from werkzeug.utils import secure_filename

import cv2
from ultralytics import YOLO
from PIL import Image

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = 'static/uploads/'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

app.config['MAX_CONTENT_LENGTH'] = 150 * 1024 * 1024  # 150 MB

app.config['UPLOAD_FOLDER'] = 'static/uploads/'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

import tempfile
import shutil

model_path = "./weights/best.pt"
model = YOLO(model_path)

class_names = {0: 'No mask', 1: 'Mask', 2: 'Incorrect'}
colors = [(0, 0, 255), (0, 255, 0), (0, 255, 255)]


def process_video(video_path):
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'processed_' + os.path.basename(video_path))
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception("Could not open video file")
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    frame_count = 0
    max_frames = 500  # Limit processing to 500 frames to avoid very long videos
    
    # Initialize stats counters
    mask_count = 0
    no_mask_count = 0
    incorrect_count = 0
    
    while cap.isOpened() and frame_count < max_frames:
        ret, frame = cap.read()
        if not ret:
            break
            
        # Process frame with YOLO model
        results = model(frame, conf=0.5, iou=0.5)[0]
        
        # Create a clean copy of the frame before drawing
        annotated_frame = frame.copy()
        
        # Draw bounding boxes and count classes
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = f"{class_names[cls]} {conf:.2f}"
            color = colors[cls]
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated_frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Update counts
            if cls == 1:
                mask_count += 1
            elif cls == 0:
                no_mask_count += 1
            elif cls == 2:
                incorrect_count += 1
        
        # Write the annotated frame
        out.write(annotated_frame)
        frame_count += 1
    
    # Release resources
    cap.release()
    out.release()
    
    stats = {
        'mask_count': mask_count,
        'no_mask_count': no_mask_count,
        'incorrect_count': incorrect_count
    }
    
    return output_path, stats

@app.route('/upload_chunk', methods=['POST'])
def upload_chunk():
    chunk = request.files.get('chunk')
    upload_id = request.form.get('upload_id')
    chunk_index = int(request.form.get('chunk_index', 0))
    total_chunks = int(request.form.get('total_chunks', 1))
    filename = request.form.get('filename')

    if not all([chunk, upload_id, filename]):
        return "Missing parameters", 400

    temp_dir = os.path.join(tempfile.gettempdir(), upload_id)
    os.makedirs(temp_dir, exist_ok=True)

    chunk_path = os.path.join(temp_dir, f"chunk_{chunk_index}")
    chunk.save(chunk_path)

    return "Chunk uploaded", 200

@app.route('/assemble_chunks', methods=['POST'])
def assemble_chunks():
    data = request.get_json()
    upload_id = data.get('upload_id')
    filename = data.get('filename')

    if not all([upload_id, filename]):
        return "Missing parameters", 400

    temp_dir = os.path.join(tempfile.gettempdir(), upload_id)
    if not os.path.exists(temp_dir):
        return "Upload ID not found", 404

    chunk_files = sorted(
        [f for f in os.listdir(temp_dir) if f.startswith('chunk_')],
        key=lambda x: int(x.split('_')[1])
    )

    output_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(filename))

    with open(output_path, 'wb') as output_file:
        for chunk_file in chunk_files:
            chunk_path = os.path.join(temp_dir, chunk_file)
            with open(chunk_path, 'rb') as cf:
                shutil.copyfileobj(cf, output_file)

    # Clean up temp chunks
    shutil.rmtree(temp_dir)

    # Process the assembled file only if it's an image
    file_ext = os.path.splitext(filename)[1].lower()
    if file_ext in ('.png', '.jpg', '.jpeg'):
        try:
            result_path, stats = process_image(output_path)
            # Redirect to result page with stats as query parameters
            return redirect(url_for('result',
                                    filename=os.path.basename(result_path),
                                    mask_count=stats['mask_count'],
                                    no_mask_count=stats['no_mask_count'],
                                    incorrect_count=stats['incorrect_count']))
        except Exception as e:
            return f"Error processing image: {str(e)}", 400
    else:
        # For non-image files (e.g., videos), just return success with file path
        return jsonify({
            'message': 'File uploaded and assembled successfully',
            'file_url': url_for('static', filename='uploads/' + secure_filename(filename))
        }), 200


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_video')
def upload_video():
    return render_template('upload_video.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    file.save(file_path)

    # Case-insensitive extension check
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext in ('.png', '.jpg', '.jpeg'):
        # Verify it's actually an image file
        try:
            Image.open(file_path)  # Verify image can be opened
            result_path, stats = process_image(file_path)
            return redirect(url_for('result', 
                               filename=os.path.basename(result_path),
                               mask_count=stats['mask_count'],
                               no_mask_count=stats['no_mask_count'],
                               incorrect_count=stats['incorrect_count']))
        except Exception as e:
            return f"Error processing image: {str(e)}", 400
    elif file_ext in ('.mp4', '.avi'):
        # Process video
        try:
            result_path, stats = process_video(file_path)
            # Redirect to video_result page to show styled page with video stream
            # Pass stats as query parameters
            return redirect(url_for('video_result', filename=os.path.basename(result_path),
                                    mask_count=stats['mask_count'],
                                    no_mask_count=stats['no_mask_count'],
                                    incorrect_count=stats['incorrect_count']))
        except Exception as e:
            return f"Error processing video: {str(e)}", 400
    else:
        return "Invalid file type", 400

@app.route('/result/<filename>')
def result(filename):
    # Build full path to the processed file
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    
    # Verify file exists
    if not os.path.exists(output_path):
        return "Result file not found", 404
        
    # Get relative path for template
    # Get relative path for template (removes 'static/' prefix)
    rel_path = output_path.replace('static/', '', 1)

    
    # Get stats from request args
    stats = {
        'mask_count': request.args.get('mask_count', 0),
        'no_mask_count': request.args.get('no_mask_count', 0),
        'incorrect_count': request.args.get('incorrect_count', 0)
    }
    
    return render_template('result.html',
                         filename=rel_path,
                         uploads_dir=app.config['UPLOAD_FOLDER'],
                         stats=stats)

@app.route('/webcam')
def webcam():
    return render_template('webcam.html')

@app.route('/video_feed')
def video_feed():
    width = int(request.args.get('width', 900))
    height = int(request.args.get('height', 700))
    return Response(generate_frames(width, height), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/video_stream')
def video_stream():
    return Response(generate_video_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

from flask import render_template

from flask import request

@app.route('/video_result/<filename>')
def video_result(filename):
    # Extract stats from query parameters
    stats = {
        'mask_count': int(request.args.get('mask_count', 0)),
        'no_mask_count': int(request.args.get('no_mask_count', 0)),
        'incorrect_count': int(request.args.get('incorrect_count', 0))
    }
    # Render the video_result.html template with the filename and stats
    return render_template('video_result.html', filename=filename, stats=stats)

@app.route('/stream_video/<filename>')
def stream_video(filename):
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(video_path):
        return "Video file not found", 404

    def generate():
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            results = model(frame, conf=0.5, iou=0.5)[0]
            # Clear previous boxes by redrawing original frame
            frame = frame.copy()
            for box in results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                label = f"{class_names[cls]} {conf:.2f}"
                color = colors[cls]
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        cap.release()

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

def process_image(image_path):
    image = Image.open(image_path)
    max_width, max_height = 800, 600
    if image.width > max_width or image.height > max_height:
        image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        resized_path = os.path.join(app.config['UPLOAD_FOLDER'], 'resized_' + os.path.basename(image_path))
        image.save(resized_path, quality=85)
        image_path = resized_path

    image = cv2.imread(image_path)
    results = model(image, conf=0.5, iou=0.5)[0]
    predicted_image = results.plot()
    output_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(image_path))

    cv2.imwrite(output_path, predicted_image, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    
    # Calculate detection statistics
    stats = {
        'mask_count': len([box for box in results.boxes if int(box.cls[0]) == 1]),
        'no_mask_count': len([box for box in results.boxes if int(box.cls[0]) == 0]),
        'incorrect_count': len([box for box in results.boxes if int(box.cls[0]) == 2])
    }
    
    return output_path, stats

def generate_frames(width, height):
    cap = cv2.VideoCapture(0)
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        frame = cv2.flip(frame, 1)  # Flip horizontally to correct mirror effect
        frame = cv2.resize(frame, (width, height))
        results = model(frame, conf=0.5, iou=0.5)[0]
        for box in results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])
            cls = int(box.cls[0])
            label = f"{class_names[cls]} {conf:.2f}"
            color = colors[cls]
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def generate_video_frames():
    video_path = request.args.get('video_path', '')
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
    frame = cv2.resize(frame, (500, 500))
    results = model(frame, conf=0.5, iou=0.5)[0]
    for box in results.boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
        conf = float(box.conf[0])
        cls = int(box.cls[0])
        label = f"{class_names[cls]} {conf:.2f}"
        color = colors[cls]
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    ret, buffer = cv2.imencode('.jpg', frame)
    frame = buffer.tobytes()
    yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


from flask import send_from_directory

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

if __name__ == '__main__':
    app.run(debug=True)
