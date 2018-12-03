import functools
import datetime as dt
import configparser
import os
from flask import (
    Blueprint, render_template, current_app, request, url_for, make_response, flash, redirect
)
from main.db import get_db
from werkzeug.exceptions import abort


bp = Blueprint('zapisy', __name__)


# Index, w którym da się zobaczyć podsumowanie nauczycieli
@bp.route('/')
def index():
    db = get_db()

    # Komunikacja z bazą
    nauczyciele = db.execute(
        'SELECT id, imie, nazwisko, obecny FROM nauczyciele'
    ).fetchall()
    
    # View
    return render_template('zapisy/index.html', nauczyciele=nauczyciele)
    
# View wyboru godziny do zapisu (tu trzeba będzie dopisać jakieś POSTy)
@bp.route('/nauczyciel/<int:id>', methods=('GET', 'POST'))
def nauczyciel(id):
    db = get_db()

    # Przetwarzanie zapytania (rezerwacji godziny)
    if request.method == 'POST':
        for key in request.form.keys(): print(key)
        imie_ucznia = request.form.get('fname')
        nazwisko_ucznia = request.form.get('lname')
        imie_rodzica = "Adam" #request.form[' ']
        nazwisko_rodzica = "Skrrrtcki" #request.form[' ']
        email = request.form.get('email')
        godzina = "21:37" #request.form[' ']
        rodo = True #request.form['rodo']
        error = None

        if not imie_ucznia:
            error = "Brakuje imienia ucznia."
        elif not nazwisko_ucznia:
            error = "Brakuje nazwiska ucznia."
        elif not email:
            error = "Brakuje adresu e-mail."
        elif not imie_rodzica:
            error = "Brakuje imienia rodzica."
        elif not nazwisko_rodzica:
            error = "Brakuje nazwiska rodzica."
        elif not rodo:
            error = "Brakuje zgody na przetwarzanie danych osobowych."
        elif not db.execute('SELECT obecny FROM nauczyciele WHERE id = ?',
                            (id,)).fetchone()['obecny']:
            error = 'Nauczyciel nie będzie obecny na dniu otwartym.'
        else:
            db.execute('BEGIN TRANSACTION')
            if db.execute('SELECT * FROM wizyty '
                          'WHERE id_nauczyciela = ? AND godzina = ?',
                          (id, godzina)).fetchone() is not None:
                error = 'Godzina jest już zajęta.'


        if error is not None:
            print(error)
            flash(error)
            if db.in_transaction:
                db.commit()
        else:          
            # Rezerwowanie terminu
            db.execute(
                'INSERT INTO wizyty '
                '(id_nauczyciela, imie_rodzica, nazwisko_rodzica, email_rodzica, '
                'imie_ucznia, nazwisko_ucznia, godzina)'
                ' VALUES (?, ?, ?, ?, ?, ?, ?)',
                (id, imie_rodzica, nazwisko_rodzica, email, imie_ucznia, nazwisko_ucznia, godzina)
            )
            db.commit()
            return redirect(url_for('index'))

    # Ustawienie wszystkich dat
    conf = configparser.ConfigParser()
    conf.read(os.path.join(current_app.instance_path, 'config.ini'))
    start = dt.datetime.strptime(
        conf['dzien otwarty']['data'] + ' ' + conf['dzien otwarty']['start'],
        '%d/%m/%Y %H:%M'
    )
    koniec = dt.datetime.strptime(
        conf['dzien otwarty']['data'] + ' ' + conf['dzien otwarty']['koniec'],
        '%d/%m/%Y %H:%M'
    )
    blok = conf['dzien otwarty']['blok']
    blok = [int(s) for s in blok.split(':')]
    blok = dt.timedelta(hours=blok[0], minutes=blok[1])

    # Komunikacja z bazą
    zajete = db.execute(
        'SELECT godzina FROM wizyty WHERE id_nauczyciela = ?', (id,)
    ).fetchall()
    zajete = [dt.datetime.strptime(
        conf['dzien otwarty']['data'] + ' ' + r['godzina'], '%d/%m/%Y %H:%M')
        for r in zajete]
    dane_nauczyciela = db.execute(
        'SELECT imie, nazwisko, obecny FROM nauczyciele WHERE id = ?', (id,)
    ).fetchone()
    if dane_nauczyciela is None:
        abort(404, 'Nauczyciel o podanym ID {0} nie znaleziony :(('.format(id))
    elif not dane_nauczyciela['obecny']:
        abort(404,
              'Nauczyciel o podanym ID {0} '
              'nie będzie obecny na dniu otwartym. :(('.format(id))
    # print (dane_nauczyciela['imie'], dane_nauczyciela['nazwisko'])

    # Liczenie wolnych godzin
    rozklad = []
    t = start
    while t < koniec:
        if t in zajete:
            rozklad.append({'start':t, 'koniec':t + blok, 'wolne':False})
        else:
            rozklad.append({'start':t, 'koniec':t + blok, 'wolne':True})
        t += blok

    return render_template('zapisy/nauczyciel.html',
                           rozklad=rozklad,
                           imie=dane_nauczyciela['imie'],
                           nazwisko=dane_nauczyciela['nazwisko'],
    )

