# ============================================================
# Studienfortschritt-Dashboard
# von Frederik Sarhane (IU14088637)
# ============================================================

import pandas as pd
from datetime import datetime, timedelta
import dash
from dash import html, dcc
from dash.dependencies import Input, Output

# ============================================================
# Hilfsfunktionen

# Wandelt unterschiedliche Darstellungen für Bestanden in einen booleschen Wert um
def parse_bestanden(val):
    if pd.isna(val):
        return False

    # Falls ein numerischer Wert übergeben wird (0 oder 1)
    if isinstance(val, (int, float)):
        try:
            return int(val) == 1
        except:
            return False

    # Stringbasierte Normalisierung
    s = str(val).strip().lower()
    true_values = {'1', '1.0', 'ja', 'j', 'yes', 'y', 'true', 'wahr', 'x', 'passed', 'bestanden'}
    false_values = {'0', '0.0', 'nein', 'n', 'no', 'false', 'f', 'nicht', 'nicht bestanden'}

    if s in true_values:
        return True
    if s in false_values:
        return False

    # Versuch Zahlenformate zu interpretieren
    try:
        return int(float(s)) == 1
    except:
        return False


# ============================================================
# Klasse: Kurs
# Repräsentiert einen einzelnen Kurs eines Semesters

class Kurs:
    def __init__(self, name, semester, note, enddatum, bestanden):
        self.name = name
        self.semester = semester

        # Note in float konvertieren, Komma wird als Dezimalpunkt interpretiert
        try:
            self.note = float(str(note).replace(",", ".")) if not pd.isna(note) else None
        except:
            self.note = None

        # Enddatum einlesen (Format dd.mm.yyyy)
        try:
            self.enddatum = datetime.strptime(str(enddatum), "%d.%m.%Y")
        except:
            self.enddatum = None

        # Bestanden-Information konvertieren
        self.bestanden = parse_bestanden(bestanden)

    @property
    def startdatum(self):
        # Berechnet das Startdatum des Kurses als 6 Monate (ca. 182 Tage) vor dem Enddatum
        if self.enddatum:
            return self.enddatum - timedelta(days=182)
        return None  


    @property
    def verbleibende_zeit_tage(self):
        # Berechnet die Anzahl der verbleibenden Tage bis zum Kursende
        if self.enddatum:
            delta = self.enddatum - datetime.now()  
            return max(delta.days, 0)  # Negativwerte werden zu 0 gemacht
        return 0  

# ============================================================
# Klasse: Semester
# Gruppiert Kurse nach Semester und berechnet Kennzahlen

class Semester:
    def __init__(self, nummer):
        # Speichert die Semesternummer (z. B. 1, 2, 3 ...)
        self.nummer = nummer
        # Liste aller Kurse, die zu diesem Semester gehören
        self.kurse = []

    def add_kurs(self, kurs):
        # Fügt dem Semester einen Kurs hinzu
        self.kurse.append(kurs)

    def durchschnittsnote(self):
        # Berechnet die durchschnittliche Note aller abgeschlossenen Kurse
        noten = [k.note for k in self.kurse if k.note is not None]
        # Gibt die gerundete Durchschnittsnote zurück, falls Noten vorhanden sind
        return round(sum(noten) / len(noten), 2) if noten else None

    def anzahl_bestanden(self):
        # Gibt die Anzahl der bestandenen Kurse zurück
        return len([k for k in self.kurse if k.bestanden])

    def fortschritt_prozent(self):
        # Berechnet den Fortschritt des Semesters in Prozent
        if len(self.kurse) == 0:
            return 0  
        return round((self.anzahl_bestanden() / len(self.kurse)) * 100, 1)

    @property
    def offene_kurse(self):
        # Gibt alle Kurse zurück, die noch nicht bestanden sind
        return [k for k in self.kurse if not k.bestanden]

    @property
    def enddatum(self):
        # Ermittelt das späteste Enddatum aller Kurse
        dates = [k.enddatum for k in self.kurse if k.enddatum is not None]
        return max(dates) if dates else None

    @property
    def verbleibende_tage_bis_semesterende(self):
        # Berechnet die verbleibenden Tage bis Semesterende
        if self.enddatum:
            delta = self.enddatum - datetime.now()  
            return max(delta.days, 0)  # Keine negativen Werte
        return 0  


# ============================================================
# Klasse: Studienplan
# Verwaltet alle Kurse und Semester aus der CSV-Datei

class Studienplan:
    def __init__(self, csv_path):
        # Liste aller Semesterobjekte
        self.semester_liste = []
        # Liste aller Kursobjekte
        self.kurse = []
        # Lädt die Daten aus der CSV-Datei
        self._lade_daten(csv_path)

    def _lade_daten(self, csv_path):
        # Liest die CSV-Datei ein und erzeugt Kurs/Semesterobjekte
        df = pd.read_csv(csv_path, encoding="latin1", sep=";")

        # Erzeugt Kursobjekte aus jeder Zeile der CSV-Datei
        for _, row in df.iterrows():
            try:
                # Holt die Semesternummer und konvertiert sie zu int
                sem_num = int(row["Semester"])
            except:
                # Falls der Wert ungültig ist Zeile überspringen
                continue

            # Erstellt ein Kursobjekt mit den Daten aus der CSV
            kurs = Kurs(
                name=row["Kurs"],
                semester=sem_num,
                note=row["Note"],
                enddatum=row["Enddatum"],
                bestanden=row["Bestanden"]
            )
            # Fügt das Kursobjekt zur Gesamtkursliste hinzu
            self.kurse.append(kurs)

        # Ermittelt alle unterschiedlichen Semesternummern und sortiert sie
        semester_nums = sorted(set([k.semester for k in self.kurse]))

        # Erzeugt für jede Semesternummer ein Semesterobjekt
        for nummer in semester_nums:
            semester_obj = Semester(nummer)

            # Fügt dem Semester alle Kurse hinzu, die zu dieser Nummer gehören
            for kurs in [k for k in self.kurse if k.semester == nummer]:
                semester_obj.add_kurs(kurs)

            # Fügt das Semester der Semesterliste hinzu
            self.semester_liste.append(semester_obj)

    def gesamtnotendurchschnitt(self):
        # Berechnet die durchschnittliche Gesamtnote über das gesamte Studium
        noten = [k.note for k in self.kurse if k.note is not None]
        # Gibt den Durchschnitt gerundet zurück oder None
        return round(sum(noten)/len(noten), 2) if noten else None

    def gesamtfortschritt(self):
        # Berechnet den Gesamtfortschritt aller Kurse in Prozent
        if len(self.kurse) == 0:
            return 0  
        bestanden = len([k for k in self.kurse if k.bestanden])
        return round((bestanden / len(self.kurse)) * 100, 1)

    def offene_kurse(self):
        # Gibt alle Kurse zurück, die noch nicht bestanden wurden
        return [k for k in self.kurse if not k.bestanden]

# ============================================================
# Dash-Webinterface

csv_path = r"C:\Users\frede\Studienfortschritt_Dashboard\Studienablaufplan.csv"
studienplan = Studienplan(csv_path)

app = dash.Dash(__name__)
app.title = "Studienfortschritt-Dashboard"

# ============================================================
# Layout der Benutzeroberfläche

app.layout = html.Div([
    html.H1(
        "Studienfortschritt-Dashboard", 
        style={"textAlign": "center", "font-family": "Segoe UI, sans-serif"}
    ),

    # Dropdown zur Semesterauswahl
    html.Div([
        html.Label("Semester auswählen:"),
        dcc.Dropdown(
            id="semester-dropdown",
            options=[{"label": f"Semester {s.nummer}", "value": s.nummer}
                     for s in studienplan.semester_liste],
            value=1  # Voreinstellung: Semester 1
        )
    ], style={"width": "30%", "display": "inline-block", "verticalAlign": "top", "margin": "10px"}),

    # Bereich für Semester- und Gesamtinformationen
    html.Div([
        html.Div(id="semester-info", style={"width": "48%", "display": "inline-block", "verticalAlign": "top"}),
        html.Div(id="gesamt-info", style={"width": "48%", "display": "inline-block", "verticalAlign": "top"})
    ])
])

# ============================================================
# Callback: Aktualisiert Dashboard bei Semesterwechsel

@app.callback(
    Output("semester-info", "children"),
    Output("gesamt-info", "children"),
    Input("semester-dropdown", "value")
)
def update_dashboard(semester_num):
    """Aktualisiert die Darstellung basierend auf dem gewählten Semester."""
    
    # Zuordnung Semesterobjekt
    sem = [s for s in studienplan.semester_liste if s.nummer == semester_num][0]

    offene = sem.offene_kurse
    abgeschlossene = [k for k in sem.kurse if k.bestanden]

    # Zeitberechnung
    remaining_days_semester = sem.verbleibende_tage_bis_semesterende
    offene_anzahl = len(offene)

    # Lernmodi:
    tage_normal = int(round(remaining_days_semester / offene_anzahl)) if offene_anzahl > 0 else 0
    tage_ueberflieger = int(round(remaining_days_semester / 8))  # angenommene maximale Kursanzahl

    # Einheitlicher Box-Stil
    box_style = {
        "border": "1px solid #ccc",
        "borderRadius": "8px",
        "padding": "15px",
        "margin": "10px 0px",
        "boxShadow": "2px 2px 5px rgba(0,0,0,0.1)",
        "font-family": "Segoe UI, sans-serif",
        "backgroundColor": "#cce5ff"
    }

    # Semesterinformationen
    semester_box = html.Div([
        html.H3(f"Semester {sem.nummer}"),

        # Kennzahlen-Box
        html.Div([
            html.P(f"Fortschritt: {sem.fortschritt_prozent()}% ({sem.anzahl_bestanden()}/{len(sem.kurse)})"),
            html.P(f"Durchschnittsnote: {sem.durchschnittsnote()}" if sem.durchschnittsnote() is not None else ""),
            html.P(f"Tage bis Semesterende: {remaining_days_semester}"),
            html.P(f"Normalmodus: ca. {tage_normal} Tage pro offenem Kurs"),
            html.P(f"Überfliegermodus: ca. {tage_ueberflieger} Tage pro Kurs (bei 8 Kursen)")
        ], style=box_style),

        # Offene Kurse
        html.Div([
            html.H4("Offene Kurse:"),
            html.Ul([html.Li(
                f"{k.name} (verbleibende Tage: {k.verbleibende_zeit_tage})",
                style={"color": "red"}) for k in offene]
            ) if offene else html.P("Keine offenen Kurse")
        ], style=box_style),

        # Abgeschlossene Kurse
        html.Div([
            html.H4("Abgeschlossene Kurse:"),
            html.Ul([html.Li(
                f"{k.name}", 
                style={"color": "green"}) for k in abgeschlossene]
            ) if abgeschlossene else html.P("Keine abgeschlossenen Kurse")
        ], style=box_style)
    ])

    #  Gesamtübersicht

    enddatum_studium = max([s.enddatum for s in studienplan.semester_liste if s.enddatum is not None])
    remaining_days_study = (enddatum_studium - datetime.now()).days if enddatum_studium else 0
    offene_gesamt_anzahl = len(studienplan.offene_kurse())

    gesamt_box = html.Div([
        html.H3("Gesamtübersicht"),
        html.Div([
            html.P(f"Gesamtfortschritt: {studienplan.gesamtfortschritt()}%"),
            html.P(f"Gesamtnotendurchschnitt: {studienplan.gesamtnotendurchschnitt()}"
                   if studienplan.gesamtnotendurchschnitt() is not None else ""),
            html.P(f"Tage bis Studienende: {remaining_days_study}"),
            html.P(f"Noch abzuschließende Kurse: {offene_gesamt_anzahl}")
        ], style=box_style)
    ])

    return semester_box, gesamt_box

# ============================================================
# Server starten

if __name__ == "__main__":
    app.run(debug=True)
