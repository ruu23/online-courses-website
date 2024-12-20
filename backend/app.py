from flask import request, jsonify 
from flask_migrate import Migrate
from sqlalchemy import or_  
from config import create_app, db
from models import Users, Playlist, Video, init_db, Comment, Like, SavedVideo, Teacher
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory
from werkzeug.security import generate_password_hash

app = create_app()

@app.route('/home')
def home():
    return 'Welcome to the homepage!'

@app.route('/static/uploads/<path:filename>')
def serve_image(filename):
    app.logger.debug(f"Serving file: {filename}")
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# get-user
@app.route('/profile', methods=["GET"])
def get_user():
    # You should get the user ID from the authentication token/session
    # For now, let's assume it comes from a query parameter
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
        
    user = Users.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get the counts for comments, likes, and saved videos
    comments_count = Comment.query.filter_by(user_id=user.id).count()
    likes_count = Like.query.filter_by(user_id=user.id).count()
    saved_videos_count = SavedVideo.query.filter_by(user_id=user.id).count()
    
    # Add the statistics and user profile data to the response
    user_data = {
        'username': user.username,
        'role': user.role,
        'imgUrl': user.img_url,
        'comments_count': comments_count,
        'likes_count': likes_count,
        'saved_videos_count': saved_videos_count
    }
    
    return jsonify(user_data), 200
    

@app.route('/register', methods=["POST"])
def register():
    data = request.get_json()  # Get JSON data from request

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    confirm_password = data.get('confirm_password')
    user_type = data.get('user_type', 'student')  # Default to student if not specified
    img_url = request.files.get('profile')  # Profile image upload

    # Validate inputs
    if not username or not email or not password or not confirm_password:
        return jsonify({'error': 'All fields are required'}), 400

    if password != confirm_password:
        return jsonify({'error': 'Passwords do not match'}), 400

    if user_type not in ['student', 'teacher']:
        return jsonify({'error': 'Invalid user type'}), 400

    # Check if user already exists
    if Users.query.filter_by(email=email).first():
        return jsonify({'error': 'User already exists'}), 400

    # Handle profile image upload
    file_path = None
    if img_url:
        filename = secure_filename(img_url.filename)
        file_path = f"/static/uploads/{username}_{filename}"
        abs_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{username}_{filename}")
        img_url.save(abs_file_path)

    try:
        # Create new user with role and optional image
        user = Users(username=username, email=email, img_url=file_path, role=user_type)
        user.set_password(password)  # You should hash the password before saving

        # Save the new user to the database
        db.session.add(user)
        db.session.commit()

        return jsonify({'message': 'User registered successfully', 'role': user.role}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# login
@app.route('/login', methods=["POST"])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('pass') 

    # Validate email and password presence
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Check if user exists
    user = Users.query.filter_by(email=email).first()
    if not user:
        return jsonify({"message": "User does not exist"}), 404

    # Check if the password is correct
    if user and user.check_password(password):
        # Successful login
        return jsonify({
            'message': f'Welcome, {user.username}!',
            'user_id': user.id,
            'username': user.username,
            'imgUrl': user.img_url,
            'role': user.role  # Send the role of the user
        }), 200
    else:
        # Authentication failed
        return jsonify({'message': 'Invalid email or password'}), 401


@app.route('/profile/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    user = Users.query.get(user_id)
    if user:
        return jsonify({
            'username': user.username,
            'email': user.email,
            'role': user.role
        }), 200
    else:
        return jsonify({'error': 'User not found'}), 404


# update-profile
@app.route('/update-profile/<int:id>', methods=['PATCH'])
def update_profile(id):
    try:
        user = Users.query.get(id)
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()  # Change this to get JSON data instead of form data
        
        # Update basic info if provided
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
            
        # Handle password update
        if 'old_pass' in data and data['old_pass']:
            if not user.check_password(data['old_pass']):
        # Get form data
                username = request.form.get("username")
                email = request.form.get("email")
                old_password = request.form.get("old_pass")
                new_password = request.form.get("new_pass")
                confirm_password = request.form.get("c_password")

        # Update basic info if provided
        if username:
            user.username = username
        if email:
            user.email = email

        # Handle password update if old password is provided
        if old_password:
            if not user.check_password(old_password):
                return jsonify({'error': 'Old password is incorrect'}), 400
            if data['new_pass'] != data['c_pass']:
                return jsonify({"error": "New password and confirm password do not match"}), 400
            user.set_password(data['new_pass'])


        # Handle image update - you'll need to handle this differently if sending as base64
        if 'img_url' in data:
            # Assuming image is sent as base64 or URL
            user.img_url = data['img_url']

        db.session.commit()
        
        # Return updated user data
        return jsonify({
            "message": "Profile updated successfully",
            "user": user.to_json()
        }), 200
        # Handle profile picture upload
        if 'img_url' in request.files:
            img_url = request.files['img_url']
            if img_url.filename != '':
                filename = secure_filename(img_url.filename) 
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"user_{id}_{filename}")
                img_url.save(file_path)
                user.img_url = file_path

        db.session.commit()
        return jsonify({"message": "Profile updated successfully"}), 200


    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
@app.route('/courses', methods=["GET"])
def courses():
    playlists = Playlist.query.all()
    return jsonify([{
        "id" : p.id,
        "title": p.title,
    } for p in playlists])

@app.route('/courses/<int:playlist_id>', methods=["GET"])
def videos(playlist_id):
    playlist = Playlist.query.get(playlist_id)

    if not playlist:
        return jsonify({"message" : " No playlist found"})
    
    videos = Video.query.filter_by(playlist_id=playlist_id).all()
    return jsonify([{
        "id" : v.id,
        "title" : v.title,
        "description" : v.description,
        "thumbnail" : v.thumbnail,
        "video_url": v.video_url
    } for v in videos])

# search bar
@app.route('/search', methods=["GET"])
def search():
    query = request.args.get("q", "")

    if not query:
        return jsonify({'message': 'Please provide a search term.'}), 404
    
    user_result = Users.query.filter(
        or_(
            Users.username.ilike(f"%{query}%"),
            Users.email.ilike(f"%{query}%"),
            Users.id.ilike(f"%{query}%"),
        ).union()
    ).all()

    playlist_result = Playlist.query.filter(
        Playlist.title.ilike(f"%{query}%")
    ).all()

    videos_result = Video.query.filter(
        Video.title.ilike(f"%{query}%"),
        Video.description.ilike(f"%{query}%"),
        Video.video_url.ilike(f"%{query}%")
    ).all()

    # Combine all results
    combined_results = {
        'users': [
            {'id': Users.id, 'name': Users.username, 'email': Users.email, 'img_url': Users.img_url}
            for user in user_result
        ],
        'videos': [
            {'id': Video.id, 'title': Video.title, 'description': Video.description, 'url': Video.video_url}
            for video in videos_result
        ],
        'playlists': [
            {'id': Playlist.id, 'tilte' : Playlist.title}
            for playlist in playlist_result
        ]
    }

    return jsonify(combined_results), 200

# videos
@app.route('/courses/<int:playlist_id>/<int:video_id>', methods=['GET'])
def get_video(playlist_id, video_id):
    playlist = Playlist.query.get(playlist_id)

    if not playlist:
        return jsonify({"error": "Playlist not found"}), 400
    video = Video.query.filter_by(id = video_id, playlist_id= playlist_id).first()

    if not video:
        return jsonify({"error": "Video not found in this playlist"}), 404
    
    return jsonify({
        "playlist_id": playlist.id,
        "playlist_title": playlist.title,
        "video_id": video.id,
        "video_title": video.title,
        "description": video.description,
        "video_url": video.video_url,
        "thumbnail": video.thumbnail
    })


@app.route('/courses/<int:playlist_id>/<int:video_id>/comment', methods=['POST'])
def comments(playlist_id, video_id):
    data = request.json
    user_id = data.get('user_id')
    video_id = data.get('video_id')
    comment_text = data.get('text')

    playlist = Playlist.query.get(playlist_id)
    if not playlist:
        return jsonify({"error": "Playlist not found"}), 400

    if not user_id:
        return jsonify({"error": " user ID require"})
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error': 'Video not found'}), 404

    comment = Comment(text=comment_text, user_id= user_id, video_id=video_id)

    db.session.add(comment)
    db.session.commit()
    return jsonify({'message': 'Comment added successfully!'}), 201

@app.route('/courses/<int:playlist_id>/<int:video_id>/like', methods = ['POST'])
def like_video(playlist_id, video_id):
    data = request.json
    user_id = data.get('user_id')
    video_id = data.get('video_id')

    playlist = Playlist.query.get(playlist_id)
    if not playlist:
        return jsonify({"error": "Playlist not found"}), 400

    if not user_id:
        return jsonify({"error": " user ID require"})
    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error': 'Video not found'}), 404
    
    # chick if liked before
    existing_like = Like.query.filter_by(user_id=user_id, video_id=video_id).first()
    if existing_like:
        return jsonify({'error': 'You already liked this video'}), 400

    like = Like(video_id=video_id, user_id=user_id)
    db.session.add(like)
    db.session.commit()

    return jsonify({'message': 'Video liked successfully!'}), 201

@app.route('/courses/<int:playlist_id>/<int:video_id>/save', methods = ['POST'])
def save_video(video_id):
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    video = Video.query.get(video_id)
    if not video:
        return jsonify({'error': 'Video not found'}), 404

    # Check if video is already saved
    existing_save = SavedVideo.query.filter_by(video_id=video_id, user_id=user_id).first()
    if existing_save:
        return jsonify({'error': 'You already saved this video'}), 400

    saved_video = SavedVideo(video_id=video_id, user_id=user_id)
    db.session.add(saved_video)
    db.session.commit()

    return jsonify({'message': 'Video saved successfully!'}), 201

# Initialize Flask-Migrate
migrate = Migrate(app, db)


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role = data.get('role', 'student')  # Default role is student

    # Hash the password for security
    hashed_password = generate_password_hash(password, method='sha256')

    # Create the user with the appropriate role
    new_user = Users(username=username, email=email, password=hashed_password, role=role)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully", "role": role}), 201



# Create a new teacher
@app.route('/teachers', methods=["POST"])
def create_teacher():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    bio = data.get("bio")
    subject = data.get("subject")
    img_url = request.files['img_url'] if 'img_url' in request.files else None

    if not name or not email:
        return jsonify({'error': 'Name and email are required'}), 400

    if Teacher.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 409

    if img_url:
        filename = secure_filename(img_url.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"teacher_{email}_{filename}")
        img_url.save(file_path)

    teacher = Teacher(name=name, email=email, bio=bio, subject=subject, img_url=file_path if img_url else None)
    db.session.add(teacher)
    db.session.commit()

    return jsonify({'message': 'Teacher created successfully'}), 201

# Get all teachers
@app.route('/teachers', methods=["GET"])
def get_teachers():
    teachers = Teacher.query.all()
    return jsonify([teacher.to_json() for teacher in teachers])

# Get teacher by ID
@app.route('/teachers/<int:id>', methods=["GET"])
def get_teacher(id):
    teacher = Teacher.query.get(id)
    if not teacher:
        return jsonify({"message": "Teacher not found"}), 404
    return jsonify(teacher.to_json())

# Update teacher 
@app.route('/teachers/<int:id>', methods=["PATCH"])
def update_teacher(id):
    teacher = Teacher.query.get(id)
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404

    data = request.json
    teacher.name = data.get("name", teacher.name)
    teacher.email = data.get("email", teacher.email)
    teacher.bio = data.get("bio", teacher.bio)
    teacher.subject = data.get("subject", teacher.subject)

    if 'img_url' in request.files:
        img_url = request.files['img_url']
        filename = secure_filename(img_url.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"teacher_{id}_{filename}")
        img_url.save(file_path)
        teacher.img_url = file_path

    db.session.commit()
    return jsonify({"message": "Teacher updated successfully"}), 200

# Delete teacher
@app.route('/teachers/<int:id>', methods=["DELETE"])
def delete_teacher(id):
    teacher = Teacher.query.get(id)
    if not teacher:
        return jsonify({'error': 'Teacher not found'}), 404

    db.session.delete(teacher)
    db.session.commit()
    return jsonify({"message": "Teacher deleted successfully"}), 200





if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_db()

    app.run(debug=True)
