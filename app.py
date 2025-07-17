from flask import Flask, request, jsonify, send_file
import requests
from PIL import Image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

app = Flask(__name__)

main_key = "ZRteam"
temp_key = "RAZOR1MON"
temp_key_expiration = datetime(2025, 8, 13)  # انتهاء الصلاحية (غير التاريخ إذا أردت)

executor = ThreadPoolExecutor(max_workers=10)

def fetch_player_info(uid, region):
    url = f'https://info-outfit-ayacte.vercel.app/player-info?uid={uid}&region={region}'
    response = requests.get(url)
    return response.json() if response.status_code == 200 else None

def fetch_and_process_image(image_url, size=None):
    try:
        response = requests.get(image_url)
        if response.status_code == 200:
            image = Image.open(BytesIO(response.content)).convert("RGBA")
            if size:
                image = image.resize(size)
            return image
        return None
    except:
        return None

@app.route('/outfit-image', methods=['GET'])
def outfit_image():
    uid = request.args.get('uid')
    region = request.args.get('region')
    key = request.args.get('key')

    if not uid or not region:
        return jsonify({'error': 'Missing uid or region'}), 400

    # التحقق من المفتاح
    if key == main_key:
        pass  # مفتاح دائم
    elif key == temp_key:
        if datetime.utcnow() > temp_key_expiration:
            return jsonify({'error': 'Temporary key expired'}), 403
    else:
        return jsonify({'error': 'Invalid or missing API key'}), 403

    player_data = fetch_player_info(uid, region)
    if not player_data:
        return jsonify({'error': 'Failed to fetch player info'}), 500

    profile = player_data.get("profileInfo", {})
    clothes_ids = profile.get("clothes", [])
    equipped_skills = profile.get("equipedSkills", [])
    pet_info = player_data.get("petInfo", {})
    pet_id = pet_info.get("id")
    weapon_ids = player_data.get("basicInfo", {}).get("weaponSkinShows", [])

    required_starts = ["211", "214", "211", "203", "204", "205", "203"]
    fallback_ids = ["211000000", "214000000", "208000000", "203000000", "204000000", "205000000", "212000000"]
    used_ids = set()
    outfit_images = []

    def fetch_outfit_image(idx, code):
        matched = None
        for oid in clothes_ids:
            str_oid = str(oid)
            if str_oid.startswith(code) and oid not in used_ids:
                matched = oid
                used_ids.add(oid)
                break
        if matched is None:
            matched = fallback_ids[idx]
        url = f'https://freefireinfo.vercel.app/icon?id={matched}'
        return fetch_and_process_image(url, size=(170, 170))

    for idx, code in enumerate(required_starts):
        outfit_images.append(executor.submit(fetch_outfit_image, idx, code))

    bg_url = 'https://iili.io/FXyDJ5l.png'
    background_image = fetch_and_process_image(bg_url, size=(1024, 1024))
    if not background_image:
        return jsonify({'error': 'Failed to fetch background image'}), 500

    positions = [
        {'x': 728, 'y': 170, 'width': 170, 'height': 170},
        {'x': 142, 'y': 142, 'width': 170, 'height': 170},
        {'x': 839, 'y': 362, 'width': 170, 'height': 170},
        {'x': 710, 'y': 763, 'width': 140, 'height': 140},
        {'x': 38,  'y': 575, 'width': 170, 'height': 170},
        {'x': 164, 'y': 752, 'width': 170, 'height': 170},
        {'x': 42,  'y': 334, 'width': 170, 'height': 170}
    ]
    # أولاً: تبادل المربع الثاني (1) مع الرابع (3)
    positions[1], positions[3] = positions[3], positions[1]

    # ثم: تبادل المربع الثاني (1 بعد التعديل) مع السابع (6)
    positions[1], positions[6] = positions[6], positions[1]

    # تبادل آخر
    positions[3], positions[1] = positions[1], positions[3]

    # رفع وتحريك المربع النهائي
    positions[6]['x'] += 10
    positions[6]['y'] -= 80

    # رفع وتحريك المربع النهائي
    positions[3]['x'] -= 14
    positions[3]['y'] += 46

    # رفع وتحريك المربع النهائي
    positions[1]['x'] -= 20
    positions[1]['y'] += 50

    for idx, future in enumerate(outfit_images):
        outfit_image = future.result()
        if outfit_image:
            pos = positions[idx]
            resized = outfit_image.resize((pos['width'], pos['height']))
            background_image.paste(resized, (pos['x'], pos['y']), resized)

    # Avatar
    avatar_id = next((skill for skill in equipped_skills if str(skill).endswith("06")), 406)

    if avatar_id:
        avatar_url = f'https://characteriroxmar.vercel.app/chars?id={avatar_id}'
        avatar_image = fetch_and_process_image(avatar_url, size=(650, 780))
        if avatar_image:
            center_x = (1024 - avatar_image.width) // 2
            center_y = 154
            background_image.paste(avatar_image, (center_x, center_y), avatar_image)

    if weapon_ids:
        weapon_id = weapon_ids[0]
        weapon_url = f'https://freefireinfo.vercel.app/icon?id={weapon_id}'
        weapon_image = fetch_and_process_image(weapon_url, size=(360, 180))
        if weapon_image:
            background_image.paste(weapon_image, (670, 564), weapon_image)

    img_io = BytesIO()
    background_image.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
