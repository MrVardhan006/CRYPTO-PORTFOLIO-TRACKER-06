from flask import Blueprint, render_template, request, flash
from flask_login import login_required
import hashlib

bp = Blueprint('cipher', __name__)

@bp.route('/cipher', methods=['GET', 'POST'])
@login_required
def cipher_page():
    results = {}
    if request.method == 'POST':
        text = request.form.get('inputText', '').strip()
        shift = request.form.get('shiftValue', type=int)
        options = request.form.getlist('options') 
        if not text:
            flash('Please enter a message.', 'error')
        else:
            if 'encrypt' in options:
                if shift is None:
                    flash('Please enter shift value for encryption.', 'error')
                else:
                    results['Encrypted:'] = encrypt(text, shift)
            if 'decrypt' in options:
                if shift is None:
                    flash('Please enter shift value for decryption.', 'error')
                else:
                    results['Decrypted:'] = decrypt(text, shift)
            if 'hash' in options:
                results['SHA-256 Hash:'] = hashlib.sha256(text.encode()).hexdigest()
    return render_template('cipher.html', results=results)
def encrypt(text, shift):
    result = ''
    for char in text:
        if char.isalpha():
            base = ord('A') if char.isupper() else ord('a')
            result += chr(((ord(char) - base + shift) % 26) + base)
        else:
            result += char
    return result
def decrypt(text, shift):
    return encrypt(text, -shift)
