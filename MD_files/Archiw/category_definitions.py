"""
Kategorie dokumentów RAG - Definicje bazowe.

Ten plik zawiera definicje wszystkich kategorii dokumentów używanych w systemie RAG.
Każda kategoria ma strukturę wielojęzyczną (PL, EN, DE) z słowami kluczowymi
do automatycznej klasyfikacji dokumentów.

Użycie:
    from backend_app.config.category_definitions import CATEGORY_TEMPLATES
    from backend_app.config.category_definitions import get_category_template
"""

# ============================================================================
# KATEGORIA: MEDYCYNA
# ============================================================================

MEDICINE_TEMPLATE = {
    "id": "medicine",
    "names": {
        "pl": "Medycyna",
        "en": "Medicine",
        "de": "Medizin"
    },
    "path": "/medycyna",
    "keywords": {
        "pl": ["lekarz", "pacjent", "leczenie", "choroba", "diagnoza", "szpital", "klinika", "badanie", "terapia", "medycyna"],
        "en": ["doctor", "patient", "treatment", "disease", "diagnosis", "hospital", "clinic", "examination", "therapy", "medicine"],
        "de": ["arzt", "patient", "behandlung", "krankheit", "diagnose", "krankenhaus", "klinik", "untersuchung", "therapie", "medizin"]
    },
    "subcategories": [
        {
            "id": "medicine.diseases",
            "names": {"pl": "Choroby", "en": "Diseases", "de": "Krankheiten"},
            "path": "/medycyna/choroby",
            "keywords": {
                "pl": ["choroba", "objawy", "rozpoznanie", "przebieg", "patologia"],
                "en": ["disease", "symptoms", "diagnosis", "course", "pathology"],
                "de": ["krankheit", "symptome", "diagnose", "verlauf", "pathologie"]
            },
            "subcategories": [
                {
                    "id": "medicine.diseases.cardiology",
                    "names": {"pl": "Choroby serca", "en": "Heart diseases", "de": "Herzerkrankungen"},
                    "path": "/medycyna/choroby/choroby_serca",
                    "keywords": {
                        "pl": ["serce", "zawał", "arytmia", "nadciśnienie", "kardiologia", "kardiolog", "ekg", "echokardiografia"],
                        "en": ["heart", "infarction", "arrhythmia", "hypertension", "cardiology", "cardiologist", "ecg", "echocardiography"],
                        "de": ["herz", "infarkt", "arrhythmie", "bluthochdruck", "kardiologie", "kardiologe", "ekg", "echokardiographie"]
                    }
                },
                {
                    "id": "medicine.diseases.respiratory",
                    "names": {"pl": "Choroby układu oddechowego", "en": "Respiratory diseases", "de": "Atemwegserkrankungen"},
                    "path": "/medycyna/choroby/choroby_ukladu_oddechowego",
                    "keywords": {
                        "pl": ["płuca", "astma", "zapalenie", "oskrzela", "dychawica", "gruźlica", "oddychanie", "pulmonologia"],
                        "en": ["lungs", "asthma", "pneumonia", "bronchi", "tuberculosis", "breathing", "pulmonology"],
                        "de": ["lunge", "asthma", "entzündung", "bronchien", "tuberkulose", "atmung", "pneumologie"]
                    }
                },
                {
                    "id": "medicine.diseases.neurology",
                    "names": {"pl": "Choroby neurologiczne", "en": "Neurological diseases", "de": "Neurologische Erkrankungen"},
                    "path": "/medycyna/choroby/choroby_neurologiczne",
                    "keywords": {
                        "pl": ["mózg", "nerwy", "padaczka", "stwardnienie", "alzheimer", "parkinson", "neurologia", "udar"],
                        "en": ["brain", "nerves", "epilepsy", "sclerosis", "alzheimer", "parkinson", "neurology", "stroke"],
                        "de": ["gehirn", "nerven", "epilepsie", "sklerose", "alzheimer", "parkinson", "neurologie", "schlaganfall"]
                    }
                },
                {
                    "id": "medicine.diseases.oncology",
                    "names": {"pl": "Choroby onkologiczne", "en": "Oncological diseases", "de": "Onkologische Erkrankungen"},
                    "path": "/medycyna/choroby/choroby_onkologiczne",
                    "keywords": {
                        "pl": ["rak", "nowotwór", "guz", "chemioterapia", "radioterapia", "onkologia", "metastazy", "biopsja"],
                        "en": ["cancer", "tumor", "chemotherapy", "radiotherapy", "oncology", "metastasis", "biopsy"],
                        "de": ["krebs", "tumor", "chemotherapie", "strahlentherapie", "onkologie", "metastase", "biopsie"]
                    }
                },
                {
                    "id": "medicine.diseases.autoimmune",
                    "names": {"pl": "Choroby autoimmunologiczne", "en": "Autoimmune diseases", "de": "Autoimmunerkrankungen"},
                    "path": "/medycyna/choroby/choroby_autoimmunologiczne",
                    "keywords": {
                        "pl": ["autoimmunologiczne", "reumatoidalne", "toczeń", "łuszczyca", "nadczynność", "przeciwciała"],
                        "en": ["autoimmune", "rheumatoid", "lupus", "psoriasis", "hyperthyroidism", "antibodies"],
                        "de": ["autoimmun", "rheumatoid", "lupus", "psoriasis", "schilddrüsenüberfunktion", "antikörper"]
                    }
                },
                {
                    "id": "medicine.diseases.infectious",
                    "names": {"pl": "Choroby zakaźne", "en": "Infectious diseases", "de": "Infektionskrankheiten"},
                    "path": "/medycyna/choroby/choroby_zakazne",
                    "keywords": {
                        "pl": ["wirus", "bakteria", "zakażenie", "grypa", "covid", "hiv", "wirusowe", "szczepionka"],
                        "en": ["virus", "bacteria", "infection", "flu", "covid", "hiv", "viral", "vaccine"],
                        "de": ["virus", "bakterie", "infektion", "grippe", "covid", "hiv", "virale", "impfstoff"]
                    }
                },
                {
                    "id": "medicine.diseases.psychiatric",
                    "names": {"pl": "Choroby psychiczne", "en": "Mental illnesses", "de": "Psychische Erkrankungen"},
                    "path": "/medycyna/choroby/choroby_psychiczne",
                    "keywords": {
                        "pl": ["depresja", "lęk", "schizofrenia", "nerwica", "psychiatria", "psychoterapia", "zaburzenia"],
                        "en": ["depression", "anxiety", "schizophrenia", "neurosis", "psychiatry", "psychotherapy", "disorders"],
                        "de": ["depression", "angst", "schizophrenie", "neurose", "psychiatrie", "psychotherapie", "störungen"]
                    }
                }
            ]
        },
        {
            "id": "medicine.pharmacology",
            "names": {"pl": "Farmakologia", "en": "Pharmacology", "de": "Pharmakologie"},
            "path": "/medycyna/farmakologia",
            "keywords": {
                "pl": ["lek", "farmaceuta", "apteka", "substancja", "dawka", "przepis", "recepta"],
                "en": ["drug", "pharmacist", "pharmacy", "substance", "dose", "prescription"],
                "de": ["medikament", "apotheker", "apotheke", "substanz", "dosis", "rezept"]
            },
            "subcategories": [
                {
                    "id": "medicine.pharmacology.prescription",
                    "names": {"pl": "Leki na receptę", "en": "Prescription drugs", "de": "Verschreibungspflichtige Medikamente"},
                    "path": "/medycyna/farmakologia/leki_na_recepte",
                    "keywords": {
                        "pl": ["recepta", "na receptę", "leki silne", "antybiotyk", "opioidy"],
                        "en": ["prescription", "prescription drugs", "antibiotics", "opioids"],
                        "de": ["rezeptpflichtig", "antibiotika", "opioide"]
                    }
                },
                {
                    "id": "medicine.pharmacology.otc",
                    "names": {"pl": "Leki bez recepty", "en": "Over-the-counter drugs", "de": "Freiverkäufliche Medikamente"},
                    "path": "/medycyna/farmakologia/leki_bez_recepty",
                    "keywords": {
                        "pl": ["bez recepty", "otc", "apteka bez recepty", "leki dostępne"],
                        "en": ["otc", "over-the-counter", "without prescription"],
                        "de": ["rezeptfrei", "freiverkäuflich"]
                    }
                },
                {
                    "id": "medicine.pharmacology.supplements",
                    "names": {"pl": "Suplementy", "en": "Supplements", "de": "Nahrungsergänzungsmittel"},
                    "path": "/medycyna/farmakologia/suplementy",
                    "keywords": {
                        "pl": ["witamina", "suplement", "minerał", "probiotyk", "omega"],
                        "en": ["vitamin", "supplement", "mineral", "probiotic", "omega"],
                        "de": ["vitamin", "ergänzung", "mineral", "probiotikum", "omega"]
                    }
                },
                {
                    "id": "medicine.pharmacology.interactions",
                    "names": {"pl": "Interakcje leków", "en": "Drug interactions", "de": "Wechselwirkungen"},
                    "path": "/medycyna/farmakologia/interakcje_lekow",
                    "keywords": {
                        "pl": ["interakcja", "niebezpieczne połączenie", "skutki uboczne", "przeciwwskazania"],
                        "en": ["interaction", "dangerous combination", "side effects", "contraindications"],
                        "de": ["wechselwirkung", "gefährliche kombination", "nebenwirkungen", "kontraindikationen"]
                    }
                },
                {
                    "id": "medicine.pharmacology.dosage",
                    "names": {"pl": "Dawki i dawkowanie", "en": "Dosage", "de": "Dosierung"},
                    "path": "/medycyna/farmakologia/dawki_i_dawkowanie",
                    "keywords": {
                        "pl": ["dawka", "dawkowanie", "ilość", "częstotliwość", "przedawkowanie"],
                        "en": ["dose", "dosage", "amount", "frequency", "overdose"],
                        "de": ["dosis", "dosierung", "menge", "häufigkeit", "überdosierung"]
                    }
                }
            ]
        },
        {
            "id": "medicine.diagnostics",
            "names": {"pl": "Diagnostyka", "en": "Diagnostics", "de": "Diagnostik"},
            "path": "/medycyna/diagnostyka",
            "keywords": {
                "pl": ["badanie", "diagnoza", "test", "wynik", "próbka"],
                "en": ["examination", "diagnosis", "test", "result", "sample"],
                "de": ["untersuchung", "diagnose", "test", "ergebnis", "probe"]
            },
            "subcategories": [
                {
                    "id": "medicine.diagnostics.blood",
                    "names": {"pl": "Badania krwi", "en": "Blood tests", "de": "Blutuntersuchungen"},
                    "path": "/medycyna/diagnostyka/badania_krwi",
                    "keywords": {
                        "pl": ["krew", "morfologia", "hemoglobina", "glukoza", "cholesterol", "próbka krwi"],
                        "en": ["blood", "blood count", "hemoglobin", "glucose", "cholesterol", "blood sample"],
                        "de": ["blut", "blutbild", "hämoglobin", "glukose", "cholesterin", "blutprobe"]
                    }
                },
                {
                    "id": "medicine.diagnostics.imaging",
                    "names": {"pl": "Badania obrazowe", "en": "Imaging studies", "de": "Bildgebende Verfahren"},
                    "path": "/medycyna/diagnostyka/badania_obrazowe",
                    "keywords": {
                        "pl": ["rtg", "tomografia", "rezonans", "usg", "mri", "ct", "obrazowanie", "rentgen"],
                        "en": ["x-ray", "tomography", "mri", "ultrasound", "ct", "imaging", "xray"],
                        "de": ["röntgen", "tomographie", "mrt", "ultraschall", "ct", "bildgebung"]
                    }
                },
                {
                    "id": "medicine.diagnostics.genetic",
                    "names": {"pl": "Badania genetyczne", "en": "Genetic testing", "de": "Genetische Untersuchungen"},
                    "path": "/medycyna/diagnostyka/badania_genetyczne",
                    "keywords": {
                        "pl": ["gen", "dna", "genetyka", "chromosom", "mutacja", "dziedziczenie"],
                        "en": ["gene", "dna", "genetics", "chromosome", "mutation", "inheritance"],
                        "de": ["gen", "dna", "genetik", "chromosom", "mutation", "vererbung"]
                    }
                },
                {
                    "id": "medicine.diagnostics.interpretation",
                    "names": {"pl": "Interpretacja wyników", "en": "Interpretation of results", "de": "Befundinterpretation"},
                    "path": "/medycyna/diagnostyka/interpretacja_wynikow",
                    "keywords": {
                        "pl": ["interpretacja", "norma", "normy", "wynik", "odchylenie", "referencyjne"],
                        "en": ["interpretation", "norm", "reference range", "result", "deviation"],
                        "de": ["interpretation", "normwert", "referenzbereich", "ergebnis", "abweichung"]
                    }
                }
            ]
        },
        {
            "id": "medicine.first_aid",
            "names": {"pl": "Pierwsza pomoc", "en": "First aid", "de": "Erste Hilfe"},
            "path": "/medycyna/pierwsza_pomoc",
            "keywords": {
                "pl": ["pomoc", "ratunek", "nagłe", "wypadek", "uraz"],
                "en": ["aid", "rescue", "emergency", "accident", "injury"],
                "de": ["hilfe", "rettung", "notfall", "unfall", "verletzung"]
            },
            "subcategories": [
                {
                    "id": "medicine.first_aid.cpr",
                    "names": {"pl": "Resuscytacja", "en": "Resuscitation", "de": "Wiederbelebung"},
                    "path": "/medycyna/pierwsza_pomoc/resuscytacja",
                    "keywords": {
                        "pl": ["resuscytacja", "masaż", "serce", "oddech", "cpr", "defibrylator", "aeds"],
                        "en": ["resuscitation", "massage", "heart", "breath", "cpr", "defibrillator", "aeds"],
                        "de": ["wiederbelebung", "massage", "herz", "atmung", "cpr", "defibrillator"]
                    }
                },
                {
                    "id": "medicine.first_aid.injuries",
                    "names": {"pl": "Urazy i oparzenia", "en": "Injuries and burns", "de": "Verletzungen und Verbrennungen"},
                    "path": "/medycyna/pierwsza_pomoc/urazy_i_oparzenia",
                    "keywords": {
                        "pl": ["oparzenie", "uraz", "rana", "skaleczenie", "krwotok", "złamanie", "stłuczenie"],
                        "en": ["burn", "injury", "wound", "cut", "hemorrhage", "fracture", "bruise"],
                        "de": ["verbrennung", "verletzung", "wunde", "schnitt", "blutung", "bruch", "prellung"]
                    }
                },
                {
                    "id": "medicine.first_aid.poisoning",
                    "names": {"pl": "Zatrucia", "en": "Poisoning", "de": "Vergiftungen"},
                    "path": "/medycyna/pierwsza_pomoc/zatrucia",
                    "keywords": {
                        "pl": ["zatrucie", "toksyna", "jad", "trucizna", "wymioty", "antidotum"],
                        "en": ["poisoning", "toxin", "venom", "poison", "vomiting", "antidote"],
                        "de": ["vergiftung", "toxin", "gift", "giftstoff", "erbrechen", "gegengift"]
                    }
                },
                {
                    "id": "medicine.first_aid.kit",
                    "names": {"pl": "Apteczka", "en": "First aid kit", "de": "Verbandskasten"},
                    "path": "/medycyna/pierwsza_pomoc/apteczka",
                    "keywords": {
                        "pl": ["apteczka", "bandaż", "gaza", "plastry", "nożyczki", "rękawiczki"],
                        "en": ["kit", "bandage", "gauze", "plasters", "scissors", "gloves"],
                        "de": ["verbandskasten", "verband", "gaze", "pflaster", "schere", "handschuhe"]
                    }
                }
            ]
        },
        {
            "id": "medicine.public_health",
            "names": {"pl": "Zdrowie publiczne", "en": "Public health", "de": "Gesundheitswesen"},
            "path": "/medycyna/zdrowie_publiczne",
            "keywords": {
                "pl": ["zdrowie", "publiczne", "społeczne", "profilaktyka", "epidemiologia"],
                "en": ["health", "public", "community", "prevention", "epidemiology"],
                "de": ["gesundheit", "öffentliches", "gemeinschaft", "prävention", "epidemiologie"]
            },
            "subcategories": [
                {
                    "id": "medicine.public_health.prevention",
                    "names": {"pl": "Profilaktyka", "en": "Prevention", "de": "Prävention"},
                    "path": "/medycyna/zdrowie_publiczne/profilaktyka",
                    "keywords": {
                        "pl": ["profilaktyka", "zapobieganie", "badania okresowe", "przegląd"],
                        "en": ["prevention", "screening", "check-up", "periodic examination"],
                        "de": ["prävention", "vorsorge", "untersuchung", "vorsorgeuntersuchung"]
                    }
                },
                {
                    "id": "medicine.public_health.vaccination",
                    "names": {"pl": "Szczepienia", "en": "Vaccination", "de": "Impfungen"},
                    "path": "/medycyna/zdrowie_publiczne/szczepienia",
                    "keywords": {
                        "pl": ["szczepionka", "szczepienie", "immunizacja", "zaszczepić", "kalendarz szczepień"],
                        "en": ["vaccine", "vaccination", "immunization", "inoculation", "vaccination schedule"],
                        "de": ["impfstoff", "impfung", "immunisierung", "impfkalender"]
                    }
                },
                {
                    "id": "medicine.public_health.diet",
                    "names": {"pl": "Dieta", "en": "Diet", "de": "Ernährung"},
                    "path": "/medycyna/zdrowie_publiczne/dieta",
                    "keywords": {
                        "pl": ["dieta", "odżywianie", "kalorie", "białko", "węglowodany", "tłuszcze", "witaminy"],
                        "en": ["diet", "nutrition", "calories", "protein", "carbohydrates", "fats", "vitamins"],
                        "de": ["diät", "ernährung", "kalorien", "eiweiß", "kohlenhydrate", "fette", "vitamine"]
                    }
                },
                {
                    "id": "medicine.public_health.rehabilitation",
                    "names": {"pl": "Sport i rehabilitacja", "en": "Sports and rehabilitation", "de": "Sport und Rehabilitation"},
                    "path": "/medycyna/zdrowie_publiczne/sport_i_rehabilitacja",
                    "keywords": {
                        "pl": ["rehabilitacja", "fizjoterapia", "ćwiczenia", "sport", "urazy sportowe"],
                        "en": ["rehabilitation", "physiotherapy", "exercises", "sports", "sports injuries"],
                        "de": ["rehabilitation", "physiotherapie", "übungen", "sport", "sportverletzungen"]
                    }
                },
                {
                    "id": "medicine.public_health.mental",
                    "names": {"pl": "Zdrowie psychiczne", "en": "Mental health", "de": "Psychische Gesundheit"},
                    "path": "/medycyna/zdrowie_publiczne/zdrowie_mentalne",
                    "keywords": {
                        "pl": ["psychiczne", "zdrowie", "stres", "wypalenie", "medytacja", "relaks"],
                        "en": ["mental", "health", "stress", "burnout", "meditation", "relaxation"],
                        "de": ["psychisch", "gesundheit", "stress", "burnout", "meditation", "entspannung"]
                    }
                }
            ]
        },
        {
            "id": "medicine.veterinary",
            "names": {"pl": "Weterynaria", "en": "Veterinary", "de": "Tiermedizin"},
            "path": "/medycyna/weterynaria",
            "keywords": {
                "pl": ["zwierzę", "weterynarz", "pies", "kot", "zwierzęta", "leczenie zwierząt"],
                "en": ["animal", "veterinarian", "dog", "cat", "animals", "veterinary"],
                "de": ["tier", "tierarzt", "hund", "katze", "tiere", "tiermedizin"]
            },
            "subcategories": [
                {
                    "id": "medicine.veterinary.diseases",
                    "names": {"pl": "Choroby zwierząt", "en": "Animal diseases", "de": "Tierkrankheiten"},
                    "path": "/medycyna/weterynaria/choroby_zwierzat",
                    "keywords": {
                        "pl": ["choroba", "zwierzę", "objawy", "leczenie", "pies", "kot", "koń", "bydło"],
                        "en": ["disease", "animal", "symptoms", "treatment", "dog", "cat", "horse", "cattle"],
                        "de": ["krankheit", "tier", "symptome", "behandlung", "hund", "katze", "pferd", "rind"]
                    }
                },
                {
                    "id": "medicine.veterinary.vaccination",
                    "names": {"pl": "Szczepienia zwierząt", "en": "Animal vaccination", "de": "Tierimpfungen"},
                    "path": "/medycyna/weterynaria/szczepienia_zwierzat",
                    "keywords": {
                        "pl": ["szczepionka", "zwierzę", "wścieklizna", "nosówka"],
                        "en": ["vaccine", "animal", "rabies", "distemper"],
                        "de": ["impfstoff", "tier", "tollwut", "staupe"]
                    }
                },
                {
                    "id": "medicine.veterinary.care",
                    "names": {"pl": "Opieka nad zwierzętami", "en": "Animal care", "de": "Tierpflege"},
                    "path": "/medycyna/weterynaria/opieka_nad_zwierzetami",
                    "keywords": {
                        "pl": ["opieka", "pielęgnacja", "karmienie", "zwierzęta domowe"],
                        "en": ["care", "grooming", "feeding", "pets"],
                        "de": ["pflege", "hautpflege", "fütterung", "haustiere"]
                    }
                }
            ]
        }
    ]
}

# ============================================================================
# GŁÓWNY SŁOWNIK KATEGORII
# ============================================================================

CATEGORY_TEMPLATES = {
    "medicine": MEDICINE_TEMPLATE,
    # Dodaj kolejne kategorie tutaj...
    # "law": LAW_TEMPLATE,
    # "finance": FINANCE_TEMPLATE,
    # itd.
}


def get_category_template(category_id: str, language: str = "pl") -> dict:
    """
    Pobiera template kategorii dla podanego języka.
    
    Args:
        category_id: Identyfikator kategorii (np. "medicine", "law")
        language: Kod języka ("pl", "en", "de")
    
    Returns:
        Dict z danymi kategorii w wybranym języku
    
    Raises:
        KeyError: Jeśli kategoria nie istnieje
        ValueError: Jeśli język nie jest wspierany
    """
    if category_id not in CATEGORY_TEMPLATES:
        raise KeyError(f"Kategoria '{category_id}' nie istnieje. Dostępne: {list(CATEGORY_TEMPLATES.keys())}")
    
    if language not in ["pl", "en", "de"]:
        raise ValueError(f"Język '{language}' nie jest wspierany. Dostępne: pl, en, de")
    
    template = CATEGORY_TEMPLATES[category_id]
    
    # Zwróć template z nazwami w wybranym języku
    result = {
        "id": template["id"],
        "name": template["names"].get(language, template["names"]["pl"]),
        "path": template["path"],
        "keywords": template["keywords"].get(language, template["keywords"]["pl"]),
        "subcategories": []
    }
    
    def process_subcategories(subcats, lang):
        processed = []
        for sub in subcats:
            item = {
                "id": sub["id"],
                "name": sub["names"].get(lang, sub["names"]["pl"]),
                "path": sub["path"],
                "keywords": sub["keywords"].get(lang, sub["keywords"]["pl"])
            }
            if "subcategories" in sub and sub["subcategories"]:
                item["subcategories"] = process_subcategories(sub["subcategories"], lang)
            processed.append(item)
        return processed
    
    if "subcategories" in template and template["subcategories"]:
        result["subcategories"] = process_subcategories(template["subcategories"], language)
    
    return result


def list_available_categories() -> list:
    """
    Zwraca listę dostępnych identyfikatorów kategorii.
    
    Returns:
        Lista stringów z identyfikatorami kategorii
    """
    return list(CATEGORY_TEMPLATES.keys())


def get_all_keywords(language: str = "pl") -> dict:
    """
    Pobiera wszystkie słowa kluczowe ze wszystkich kategorii.
    
    Args:
        language: Kod języka ("pl", "en", "de")
    
    Returns:
        Dict {category_id: [keywords]}
    """
    result = {}
    for cat_id, template in CATEGORY_TEMPLATES.items():
        result[cat_id] = template["keywords"].get(language, template["keywords"]["pl"])
        
        # Dodaj słowa kluczowe z podkategorii
        def collect_sub_keywords(subcats, lang):
            keywords = []
            for sub in subcats:
                keywords.extend(sub["keywords"].get(lang, sub["keywords"]["pl"]))
                if "subcategories" in sub:
                    keywords.extend(collect_sub_keywords(sub["subcategories"], lang))
            return keywords
        
        if "subcategories" in template:
            result[cat_id].extend(collect_sub_keywords(template["subcategories"], language))
    
    return result