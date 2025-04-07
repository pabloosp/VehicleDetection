from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta'  # Cambia esta clave en producción

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
