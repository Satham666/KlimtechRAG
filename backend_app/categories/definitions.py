"""
Definicje wszystkich 14 kategorii tematycznych RAG.

Struktura każdej kategorii:
    id          - identyfikator angielski (używany w Qdrant metadata)
    names       - nazwy pl/en/de (dla UI)
    path        - ścieżka katalogu (dla Nextcloud i path-based classification)
    path_hints  - dodatkowe słowa kluczowe w ścieżce (dla path-based detection)
    keywords    - słowa kluczowe pl/en/de (dla keyword-based classification)
    subcategories - lista podkategorii (dla struktury folderów Nextcloud)
"""

# ============================================================================
# 1. MEDYCYNA / MEDICINE
# ============================================================================
MEDICINE = {
    "id": "medicine",
    "names": {"pl": "Medycyna", "en": "Medicine", "de": "Medizin"},
    "path": "/medycyna",
    "path_hints": ["medycyna", "medyczny", "medicine", "medical", "medizin", "medizinisch"],
    "keywords": {
        "pl": ["lekarz", "pacjent", "leczenie", "choroba", "diagnoza", "szpital",
               "klinika", "badanie", "terapia", "medycyna", "farmacja", "operacja",
               "zdrowie", "symptom", "recepta", "chirurg", "ortopeda", "internista"],
        "en": ["doctor", "patient", "treatment", "disease", "diagnosis", "hospital",
               "clinic", "examination", "therapy", "medicine", "pharmacy", "surgery",
               "health", "symptom", "prescription", "surgeon", "physician"],
        "de": ["arzt", "patient", "behandlung", "krankheit", "diagnose", "krankenhaus",
               "klinik", "untersuchung", "therapie", "medizin", "apotheke", "operation",
               "gesundheit", "symptom", "rezept", "chirurg"],
    },
    "subcategories": [
        {
            "id": "medicine.diseases",
            "names": {"pl": "Choroby", "en": "Diseases", "de": "Krankheiten"},
            "path": "/medycyna/choroby",
            "subcategories": [
                {"id": "medicine.diseases.cardiology", "names": {"pl": "Choroby serca", "en": "Heart diseases", "de": "Herzerkrankungen"}, "path": "/medycyna/choroby/choroby_serca"},
                {"id": "medicine.diseases.respiratory", "names": {"pl": "Choroby układu oddechowego", "en": "Respiratory diseases", "de": "Atemwegserkrankungen"}, "path": "/medycyna/choroby/choroby_ukladu_oddechowego"},
                {"id": "medicine.diseases.neurology", "names": {"pl": "Choroby neurologiczne", "en": "Neurological diseases", "de": "Neurologische Erkrankungen"}, "path": "/medycyna/choroby/choroby_neurologiczne"},
                {"id": "medicine.diseases.oncology", "names": {"pl": "Choroby onkologiczne", "en": "Oncological diseases", "de": "Onkologische Erkrankungen"}, "path": "/medycyna/choroby/choroby_onkologiczne"},
                {"id": "medicine.diseases.autoimmune", "names": {"pl": "Choroby autoimmunologiczne", "en": "Autoimmune diseases", "de": "Autoimmunerkrankungen"}, "path": "/medycyna/choroby/choroby_autoimmunologiczne"},
                {"id": "medicine.diseases.infectious", "names": {"pl": "Choroby zakaźne", "en": "Infectious diseases", "de": "Infektionskrankheiten"}, "path": "/medycyna/choroby/choroby_zakazne"},
                {"id": "medicine.diseases.psychiatric", "names": {"pl": "Choroby psychiczne", "en": "Mental illnesses", "de": "Psychische Erkrankungen"}, "path": "/medycyna/choroby/choroby_psychiczne"},
            ],
        },
        {
            "id": "medicine.pharmacology",
            "names": {"pl": "Farmakologia", "en": "Pharmacology", "de": "Pharmakologie"},
            "path": "/medycyna/farmakologia",
            "subcategories": [
                {"id": "medicine.pharmacology.prescription", "names": {"pl": "Leki na receptę", "en": "Prescription drugs", "de": "Rezeptpflichtige Medikamente"}, "path": "/medycyna/farmakologia/leki_na_recepte"},
                {"id": "medicine.pharmacology.otc", "names": {"pl": "Leki bez recepty", "en": "OTC drugs", "de": "Rezeptfreie Medikamente"}, "path": "/medycyna/farmakologia/leki_bez_recepty"},
                {"id": "medicine.pharmacology.supplements", "names": {"pl": "Suplementy", "en": "Supplements", "de": "Nahrungsergänzungsmittel"}, "path": "/medycyna/farmakologia/suplementy"},
                {"id": "medicine.pharmacology.interactions", "names": {"pl": "Interakcje leków", "en": "Drug interactions", "de": "Wechselwirkungen"}, "path": "/medycyna/farmakologia/interakcje_lekow"},
                {"id": "medicine.pharmacology.dosage", "names": {"pl": "Dawki i dawkowanie", "en": "Dosage", "de": "Dosierung"}, "path": "/medycyna/farmakologia/dawki_i_dawkowanie"},
            ],
        },
        {
            "id": "medicine.diagnostics",
            "names": {"pl": "Diagnostyka", "en": "Diagnostics", "de": "Diagnostik"},
            "path": "/medycyna/diagnostyka",
            "subcategories": [
                {"id": "medicine.diagnostics.blood", "names": {"pl": "Badania krwi", "en": "Blood tests", "de": "Blutuntersuchungen"}, "path": "/medycyna/diagnostyka/badania_krwi"},
                {"id": "medicine.diagnostics.imaging", "names": {"pl": "Badania obrazowe", "en": "Imaging studies", "de": "Bildgebende Verfahren"}, "path": "/medycyna/diagnostyka/badania_obrazowe"},
                {"id": "medicine.diagnostics.genetic", "names": {"pl": "Badania genetyczne", "en": "Genetic testing", "de": "Genetische Untersuchungen"}, "path": "/medycyna/diagnostyka/badania_genetyczne"},
                {"id": "medicine.diagnostics.interpretation", "names": {"pl": "Interpretacja wyników", "en": "Results interpretation", "de": "Befundinterpretation"}, "path": "/medycyna/diagnostyka/interpretacja_wynikow"},
            ],
        },
        {
            "id": "medicine.first_aid",
            "names": {"pl": "Pierwsza pomoc", "en": "First aid", "de": "Erste Hilfe"},
            "path": "/medycyna/pierwsza_pomoc",
            "subcategories": [
                {"id": "medicine.first_aid.cpr", "names": {"pl": "Resuscytacja", "en": "Resuscitation", "de": "Wiederbelebung"}, "path": "/medycyna/pierwsza_pomoc/resuscytacja"},
                {"id": "medicine.first_aid.injuries", "names": {"pl": "Urazy i oparzenia", "en": "Injuries and burns", "de": "Verletzungen und Verbrennungen"}, "path": "/medycyna/pierwsza_pomoc/urazy_i_oparzenia"},
                {"id": "medicine.first_aid.poisoning", "names": {"pl": "Zatrucia", "en": "Poisoning", "de": "Vergiftungen"}, "path": "/medycyna/pierwsza_pomoc/zatrucia"},
                {"id": "medicine.first_aid.kit", "names": {"pl": "Apteczka", "en": "First aid kit", "de": "Verbandskasten"}, "path": "/medycyna/pierwsza_pomoc/apteczka"},
            ],
        },
        {
            "id": "medicine.public_health",
            "names": {"pl": "Zdrowie publiczne", "en": "Public health", "de": "Gesundheitswesen"},
            "path": "/medycyna/zdrowie_publiczne",
            "subcategories": [
                {"id": "medicine.public_health.prevention", "names": {"pl": "Profilaktyka", "en": "Prevention", "de": "Prävention"}, "path": "/medycyna/zdrowie_publiczne/profilaktyka"},
                {"id": "medicine.public_health.vaccination", "names": {"pl": "Szczepienia", "en": "Vaccination", "de": "Impfungen"}, "path": "/medycyna/zdrowie_publiczne/szczepienia"},
                {"id": "medicine.public_health.diet", "names": {"pl": "Dieta", "en": "Diet", "de": "Ernährung"}, "path": "/medycyna/zdrowie_publiczne/dieta"},
                {"id": "medicine.public_health.rehabilitation", "names": {"pl": "Sport i rehabilitacja", "en": "Sports and rehabilitation", "de": "Sport und Rehabilitation"}, "path": "/medycyna/zdrowie_publiczne/sport_i_rehabilitacja"},
                {"id": "medicine.public_health.mental", "names": {"pl": "Zdrowie psychiczne", "en": "Mental health", "de": "Psychische Gesundheit"}, "path": "/medycyna/zdrowie_publiczne/zdrowie_mentalne"},
            ],
        },
        {
            "id": "medicine.veterinary",
            "names": {"pl": "Weterynaria", "en": "Veterinary", "de": "Tiermedizin"},
            "path": "/medycyna/weterynaria",
            "subcategories": [
                {"id": "medicine.veterinary.diseases", "names": {"pl": "Choroby zwierząt", "en": "Animal diseases", "de": "Tierkrankheiten"}, "path": "/medycyna/weterynaria/choroby_zwierzat"},
                {"id": "medicine.veterinary.vaccination", "names": {"pl": "Szczepienia zwierząt", "en": "Animal vaccination", "de": "Tierimpfungen"}, "path": "/medycyna/weterynaria/szczepienia_zwierzat"},
                {"id": "medicine.veterinary.care", "names": {"pl": "Opieka nad zwierzętami", "en": "Animal care", "de": "Tierpflege"}, "path": "/medycyna/weterynaria/opieka_nad_zwierzetami"},
            ],
        },
    ],
}

# ============================================================================
# 2. PRAWO / LAW
# ============================================================================
LAW = {
    "id": "law",
    "names": {"pl": "Prawo", "en": "Law", "de": "Recht"},
    "path": "/prawo",
    "path_hints": ["prawo", "prawny", "prawniczy", "law", "legal", "recht", "rechtlich", "juristisch"],
    "keywords": {
        "pl": ["prawo", "ustawa", "kodeks", "sąd", "adwokat", "prawnik", "umowa",
               "przepis", "wyrok", "pozew", "ugoda", "pełnomocnik", "notariusz",
               "kontrakt", "regulacja", "paragraf", "statut", "kancelaria"],
        "en": ["law", "act", "code", "court", "lawyer", "attorney", "contract",
               "regulation", "judgment", "lawsuit", "settlement", "notary",
               "statute", "legal", "legislation", "clause", "firm"],
        "de": ["recht", "gesetz", "gesetzbuch", "gericht", "anwalt", "rechtsanwalt",
               "vertrag", "vorschrift", "urteil", "klage", "notar", "statute",
               "regelung", "paragraph", "kanzlei"],
    },
    "subcategories": [
        {
            "id": "law.civil",
            "names": {"pl": "Prawo cywilne", "en": "Civil law", "de": "Zivilrecht"},
            "path": "/prawo/cywilne",
            "subcategories": [
                {"id": "law.civil.contracts", "names": {"pl": "Umowy", "en": "Contracts", "de": "Verträge"}, "path": "/prawo/cywilne/umowy"},
                {"id": "law.civil.inheritance", "names": {"pl": "Spadki", "en": "Inheritance", "de": "Erbrecht"}, "path": "/prawo/cywilne/spadki"},
                {"id": "law.civil.family", "names": {"pl": "Prawo rodzinne", "en": "Family law", "de": "Familienrecht"}, "path": "/prawo/cywilne/prawo_rodzinne"},
                {"id": "law.civil.liability", "names": {"pl": "Odpowiedzialność cywilna", "en": "Civil liability", "de": "Zivilhaftung"}, "path": "/prawo/cywilne/odpowiedzialnosc_cywilna"},
                {"id": "law.civil.data_protection", "names": {"pl": "Ochrona danych osobowych", "en": "Data protection", "de": "Datenschutz"}, "path": "/prawo/cywilne/ochrona_danych_osobowych"},
            ],
        },
        {
            "id": "law.criminal",
            "names": {"pl": "Prawo karne", "en": "Criminal law", "de": "Strafrecht"},
            "path": "/prawo/karne",
            "subcategories": [
                {"id": "law.criminal.offenses", "names": {"pl": "Przestępstwa", "en": "Offenses", "de": "Straftaten"}, "path": "/prawo/karne/przestepstwa"},
                {"id": "law.criminal.penalties", "names": {"pl": "Kary", "en": "Penalties", "de": "Strafen"}, "path": "/prawo/karne/kary"},
                {"id": "law.criminal.procedure", "names": {"pl": "Procedura karna", "en": "Criminal procedure", "de": "Strafverfahren"}, "path": "/prawo/karne/procedura_karna"},
                {"id": "law.criminal.rights", "names": {"pl": "Prawa oskarżonego", "en": "Defendant rights", "de": "Rechte des Angeklagten"}, "path": "/prawo/karne/prawa_oskarzonego"},
            ],
        },
        {
            "id": "law.administrative",
            "names": {"pl": "Prawo administracyjne", "en": "Administrative law", "de": "Verwaltungsrecht"},
            "path": "/prawo/administracyjne",
            "subcategories": [
                {"id": "law.administrative.public", "names": {"pl": "Administracja publiczna", "en": "Public administration", "de": "Öffentliche Verwaltung"}, "path": "/prawo/administracyjne/administracja_publiczna"},
                {"id": "law.administrative.permits", "names": {"pl": "Pozwolenia i koncesje", "en": "Permits and licenses", "de": "Genehmigungen und Lizenzen"}, "path": "/prawo/administracyjne/pozwolenia_i_koncesje"},
                {"id": "law.administrative.local", "names": {"pl": "Samorząd", "en": "Local government", "de": "Kommunalverwaltung"}, "path": "/prawo/administracyjne/samorzad"},
                {"id": "law.administrative.construction", "names": {"pl": "Prawo budowlane", "en": "Construction law", "de": "Baurecht"}, "path": "/prawo/administracyjne/prawo_budowlane"},
            ],
        },
        {
            "id": "law.labor",
            "names": {"pl": "Prawo pracy", "en": "Labor law", "de": "Arbeitsrecht"},
            "path": "/prawo/praca",
            "subcategories": [
                {"id": "law.labor.contracts", "names": {"pl": "Umowy o pracę", "en": "Employment contracts", "de": "Arbeitsverträge"}, "path": "/prawo/praca/umowy_o_prace"},
                {"id": "law.labor.employee_rights", "names": {"pl": "Prawa pracownika", "en": "Employee rights", "de": "Arbeitnehmerrechte"}, "path": "/prawo/praca/prawa_pracownika"},
                {"id": "law.labor.employer_duties", "names": {"pl": "Obowiązki pracodawcy", "en": "Employer duties", "de": "Arbeitgeberpflichten"}, "path": "/prawo/praca/obowiazki_pracodawcy"},
                {"id": "law.labor.dismissal", "names": {"pl": "Zwolnienia i redukcje", "en": "Dismissal and layoffs", "de": "Kündigung und Entlassungen"}, "path": "/prawo/praca/zwolnienia_i_redukcje"},
                {"id": "law.labor.safety", "names": {"pl": "BHP", "en": "Occupational safety", "de": "Arbeitssicherheit"}, "path": "/prawo/praca/bhp"},
            ],
        },
        {
            "id": "law.commercial",
            "names": {"pl": "Prawo handlowe", "en": "Commercial law", "de": "Handelsrecht"},
            "path": "/prawo/handlowe",
            "subcategories": [
                {"id": "law.commercial.registry", "names": {"pl": "Rejestr firm", "en": "Business registry", "de": "Firmenregister"}, "path": "/prawo/handlowe/rejestr_firm"},
                {"id": "law.commercial.contracts", "names": {"pl": "Umowy handlowe", "en": "Commercial contracts", "de": "Handelsverträge"}, "path": "/prawo/handlowe/umowy_handlowe"},
                {"id": "law.commercial.competition", "names": {"pl": "Prawo konkurencji", "en": "Competition law", "de": "Wettbewerbsrecht"}, "path": "/prawo/handlowe/prawo_konkurencji"},
                {"id": "law.commercial.bankruptcy", "names": {"pl": "Prawo upadłościowe", "en": "Bankruptcy law", "de": "Insolvenzrecht"}, "path": "/prawo/handlowe/prawo_upadlosciowe"},
            ],
        },
        {
            "id": "law.tax",
            "names": {"pl": "Prawo podatkowe", "en": "Tax law", "de": "Steuerrecht"},
            "path": "/prawo/podatkowe",
            "subcategories": [
                {"id": "law.tax.pit", "names": {"pl": "PIT", "en": "Personal income tax", "de": "Einkommensteuer"}, "path": "/prawo/podatkowe/pit"},
                {"id": "law.tax.vat", "names": {"pl": "VAT", "en": "VAT", "de": "Mehrwertsteuer"}, "path": "/prawo/podatkowe/vat"},
                {"id": "law.tax.cit", "names": {"pl": "CIT", "en": "Corporate income tax", "de": "Körperschaftsteuer"}, "path": "/prawo/podatkowe/cit"},
                {"id": "law.tax.local", "names": {"pl": "Podatki lokalne", "en": "Local taxes", "de": "Kommunalsteuern"}, "path": "/prawo/podatkowe/podatki_lokalne"},
                {"id": "law.tax.optimization", "names": {"pl": "Optymalizacja podatkowa", "en": "Tax optimization", "de": "Steueroptimierung"}, "path": "/prawo/podatkowe/optymalizacja_podatkowa"},
            ],
        },
        {
            "id": "law.international",
            "names": {"pl": "Prawo międzynarodowe", "en": "International law", "de": "Internationales Recht"},
            "path": "/prawo/miedzynarodowe",
            "subcategories": [
                {"id": "law.international.eu", "names": {"pl": "Unia Europejska", "en": "European Union", "de": "Europäische Union"}, "path": "/prawo/miedzynarodowe/unia_europejska"},
                {"id": "law.international.treaties", "names": {"pl": "Traktaty i umowy", "en": "Treaties and agreements", "de": "Verträge und Abkommen"}, "path": "/prawo/miedzynarodowe/traktaty_i_umowy"},
                {"id": "law.international.extradition", "names": {"pl": "Ekstradycja", "en": "Extradition", "de": "Auslieferung"}, "path": "/prawo/miedzynarodowe/ekstradycja"},
            ],
        },
    ],
}

# ============================================================================
# 3. FINANSE / FINANCE
# ============================================================================
FINANCE = {
    "id": "finance",
    "names": {"pl": "Finanse", "en": "Finance", "de": "Finanzen"},
    "path": "/finanse",
    "path_hints": ["finanse", "finansowy", "finance", "financial", "finanzen", "finanziell"],
    "keywords": {
        "pl": ["finanse", "pieniądze", "konto", "bank", "kredyt", "inwestycja",
               "budżet", "podatek", "ubezpieczenie", "giełda", "oszczędności",
               "pożyczka", "obligacje", "akcje", "procent", "lokata", "faktura"],
        "en": ["finance", "money", "account", "bank", "credit", "investment",
               "budget", "tax", "insurance", "stock exchange", "savings",
               "loan", "bonds", "shares", "interest", "deposit", "invoice"],
        "de": ["finanzen", "geld", "konto", "bank", "kredit", "investition",
               "haushalt", "steuer", "versicherung", "börse", "ersparnisse",
               "darlehen", "anleihen", "aktien", "zinsen", "einlage", "rechnung"],
    },
    "subcategories": [
        {
            "id": "finance.banking",
            "names": {"pl": "Bankowość", "en": "Banking", "de": "Bankwesen"},
            "path": "/finanse/bankowosc",
            "subcategories": [
                {"id": "finance.banking.personal", "names": {"pl": "Konta osobiste", "en": "Personal accounts", "de": "Privatkonten"}, "path": "/finanse/bankowosc/konta_osobiste"},
                {"id": "finance.banking.business", "names": {"pl": "Konta firmowe", "en": "Business accounts", "de": "Geschäftskonten"}, "path": "/finanse/bankowosc/konta_firmowe"},
                {"id": "finance.banking.loans", "names": {"pl": "Kredyty i pożyczki", "en": "Loans and credits", "de": "Kredite und Darlehen"}, "path": "/finanse/bankowosc/kredyty_i_pozyczki"},
                {"id": "finance.banking.cards", "names": {"pl": "Karty kredytowe", "en": "Credit cards", "de": "Kreditkarten"}, "path": "/finanse/bankowosc/karty_kredytowe"},
                {"id": "finance.banking.transfers", "names": {"pl": "Przelewy", "en": "Transfers", "de": "Überweisungen"}, "path": "/finanse/bankowosc/przelewy"},
            ],
        },
        {
            "id": "finance.investments",
            "names": {"pl": "Inwestycje", "en": "Investments", "de": "Investitionen"},
            "path": "/finanse/inwestycje",
            "subcategories": [
                {"id": "finance.investments.stocks", "names": {"pl": "Giełda", "en": "Stock exchange", "de": "Börse"}, "path": "/finanse/inwestycje/gielda"},
                {"id": "finance.investments.bonds", "names": {"pl": "Obligacje", "en": "Bonds", "de": "Anleihen"}, "path": "/finanse/inwestycje/obligacje"},
                {"id": "finance.investments.funds", "names": {"pl": "Fundusze inwestycyjne", "en": "Investment funds", "de": "Investmentfonds"}, "path": "/finanse/inwestycje/fundusze_inwestycyjne"},
                {"id": "finance.investments.crypto", "names": {"pl": "Kryptowaluty", "en": "Cryptocurrencies", "de": "Kryptowährungen"}, "path": "/finanse/inwestycje/kryptowaluty"},
                {"id": "finance.investments.real_estate", "names": {"pl": "Nieruchomości", "en": "Real estate", "de": "Immobilien"}, "path": "/finanse/inwestycje/nieruchomosci"},
                {"id": "finance.investments.commodities", "names": {"pl": "Złoto i surowce", "en": "Gold and commodities", "de": "Gold und Rohstoffe"}, "path": "/finanse/inwestycje/zloto_i_surowce"},
            ],
        },
        {
            "id": "finance.insurance",
            "names": {"pl": "Ubezpieczenia", "en": "Insurance", "de": "Versicherungen"},
            "path": "/finanse/ubezpieczenia",
            "subcategories": [
                {"id": "finance.insurance.life", "names": {"pl": "Ubezpieczenia życiowe", "en": "Life insurance", "de": "Lebensversicherung"}, "path": "/finanse/ubezpieczenia/zyciowe"},
                {"id": "finance.insurance.health", "names": {"pl": "Ubezpieczenia zdrowotne", "en": "Health insurance", "de": "Krankenversicherung"}, "path": "/finanse/ubezpieczenia/zdrowotne"},
                {"id": "finance.insurance.property", "names": {"pl": "Ubezpieczenia majątkowe", "en": "Property insurance", "de": "Sachversicherung"}, "path": "/finanse/ubezpieczenia/majatkowe"},
                {"id": "finance.insurance.car", "names": {"pl": "Ubezpieczenia samochodowe", "en": "Car insurance", "de": "Kfz-Versicherung"}, "path": "/finanse/ubezpieczenia/samochodowe"},
                {"id": "finance.insurance.travel", "names": {"pl": "Ubezpieczenia turystyczne", "en": "Travel insurance", "de": "Reiseversicherung"}, "path": "/finanse/ubezpieczenia/turystyczne"},
            ],
        },
        {
            "id": "finance.personal_tax",
            "names": {"pl": "Podatki osobiste", "en": "Personal taxes", "de": "Persönliche Steuern"},
            "path": "/finanse/podatki_osobiste",
            "subcategories": [
                {"id": "finance.personal_tax.annual", "names": {"pl": "Rozliczenia roczne", "en": "Annual tax returns", "de": "Jahressteuererklärung"}, "path": "/finanse/podatki_osobiste/rozliczenia_roczne"},
                {"id": "finance.personal_tax.deductions", "names": {"pl": "Ulgi i odliczenia", "en": "Deductions and reliefs", "de": "Abzüge und Freibeträge"}, "path": "/finanse/podatki_osobiste/ulgi_i_odliczenia"},
            ],
        },
        {
            "id": "finance.household_budget",
            "names": {"pl": "Budżet domowy", "en": "Household budget", "de": "Haushaltsbudget"},
            "path": "/finanse/budzet_domowy",
            "subcategories": [
                {"id": "finance.household_budget.planning", "names": {"pl": "Planowanie", "en": "Planning", "de": "Planung"}, "path": "/finanse/budzet_domowy/planowanie"},
                {"id": "finance.household_budget.saving", "names": {"pl": "Oszczędzanie", "en": "Saving", "de": "Sparen"}, "path": "/finanse/budzet_domowy/oszczedzanie"},
                {"id": "finance.household_budget.debt", "names": {"pl": "Długi i windykacja", "en": "Debt and collection", "de": "Schulden und Inkasso"}, "path": "/finanse/budzet_domowy/dlugi_i_windykacja"},
                {"id": "finance.household_budget.pension", "names": {"pl": "Emerytura", "en": "Pension", "de": "Rente"}, "path": "/finanse/budzet_domowy/emerytura"},
            ],
        },
        {
            "id": "finance.accounting",
            "names": {"pl": "Księgowość", "en": "Accounting", "de": "Buchhaltung"},
            "path": "/finanse/ksiegowosc",
            "subcategories": [
                {"id": "finance.accounting.records", "names": {"pl": "Ewidencja", "en": "Records", "de": "Buchführung"}, "path": "/finanse/ksiegowosc/ewidencja"},
                {"id": "finance.accounting.invoices", "names": {"pl": "Faktury", "en": "Invoices", "de": "Rechnungen"}, "path": "/finanse/ksiegowosc/faktury"},
                {"id": "finance.accounting.depreciation", "names": {"pl": "Amortyzacja", "en": "Depreciation", "de": "Abschreibung"}, "path": "/finanse/ksiegowosc/amortyzacja"},
                {"id": "finance.accounting.reports", "names": {"pl": "Sprawozdania", "en": "Financial reports", "de": "Jahresabschlüsse"}, "path": "/finanse/ksiegowosc/sprawozdania"},
            ],
        },
    ],
}

# ============================================================================
# 4. TECHNOLOGIA / TECHNOLOGY
# ============================================================================
TECHNOLOGY = {
    "id": "technology",
    "names": {"pl": "Technologia", "en": "Technology", "de": "Technologie"},
    "path": "/technologia",
    "path_hints": ["technologia", "technika", "technology", "technical", "technologie", "technisch",
                   "informatyka", "it", "computer", "computing", "software", "hardware"],
    "keywords": {
        "pl": ["technologia", "komputer", "oprogramowanie", "sprzęt", "sieć", "internet",
               "programowanie", "algorytm", "system", "baza danych", "bezpieczeństwo",
               "automatyzacja", "robotyka", "elektronika", "mikrokontroler", "telekomunikacja"],
        "en": ["technology", "computer", "software", "hardware", "network", "internet",
               "programming", "algorithm", "system", "database", "security",
               "automation", "robotics", "electronics", "microcontroller", "telecommunications"],
        "de": ["technologie", "computer", "software", "hardware", "netzwerk", "internet",
               "programmierung", "algorithmus", "system", "datenbank", "sicherheit",
               "automatisierung", "robotik", "elektronik", "mikrocontroller", "telekommunikation"],
    },
    "subcategories": [
        {
            "id": "technology.it",
            "names": {"pl": "Informatyka", "en": "Computer science", "de": "Informatik"},
            "path": "/technologia/informatyka",
            "subcategories": [
                {"id": "technology.it.programming", "names": {"pl": "Programowanie", "en": "Programming", "de": "Programmierung"}, "path": "/technologia/informatyka/programowanie"},
                {"id": "technology.it.os", "names": {"pl": "Systemy operacyjne", "en": "Operating systems", "de": "Betriebssysteme"}, "path": "/technologia/informatyka/systemy_operacyjne"},
                {"id": "technology.it.networking", "names": {"pl": "Sieci komputerowe", "en": "Computer networks", "de": "Computernetzwerke"}, "path": "/technologia/informatyka/sieci_komputerowe"},
                {"id": "technology.it.databases", "names": {"pl": "Bazy danych", "en": "Databases", "de": "Datenbanken"}, "path": "/technologia/informatyka/bazy_danych"},
                {"id": "technology.it.cybersecurity", "names": {"pl": "Cyberbezpieczeństwo", "en": "Cybersecurity", "de": "Cybersicherheit"}, "path": "/technologia/informatyka/cyberbezpieczenstwo"},
                {"id": "technology.it.cloud", "names": {"pl": "Chmura i DevOps", "en": "Cloud and DevOps", "de": "Cloud und DevOps"}, "path": "/technologia/informatyka/chmura_i_devops"},
            ],
        },
        {
            "id": "technology.electronics",
            "names": {"pl": "Elektronika", "en": "Electronics", "de": "Elektronik"},
            "path": "/technologia/elektronika",
            "subcategories": [
                {"id": "technology.electronics.circuits", "names": {"pl": "Układy scalone", "en": "Integrated circuits", "de": "Integrierte Schaltkreise"}, "path": "/technologia/elektronika/uklady_scalone"},
                {"id": "technology.electronics.microcontrollers", "names": {"pl": "Mikrokontrolery", "en": "Microcontrollers", "de": "Mikrocontroller"}, "path": "/technologia/elektronika/mikrokontrolery"},
                {"id": "technology.electronics.arduino", "names": {"pl": "Arduino i Raspberry", "en": "Arduino and Raspberry", "de": "Arduino und Raspberry"}, "path": "/technologia/elektronika/arduino_i_raspberry"},
                {"id": "technology.electronics.repair", "names": {"pl": "Naprawa sprzętu", "en": "Hardware repair", "de": "Hardwarereparatur"}, "path": "/technologia/elektronika/naprawa_sprzetu"},
            ],
        },
        {
            "id": "technology.telecom",
            "names": {"pl": "Telekomunikacja", "en": "Telecommunications", "de": "Telekommunikation"},
            "path": "/technologia/telekomunikacja",
            "subcategories": [
                {"id": "technology.telecom.mobile", "names": {"pl": "Sieci komórkowe", "en": "Mobile networks", "de": "Mobilfunknetze"}, "path": "/technologia/telekomunikacja/sieci_komorkowe"},
                {"id": "technology.telecom.internet", "names": {"pl": "Internet", "en": "Internet", "de": "Internet"}, "path": "/technologia/telekomunikacja/internet"},
                {"id": "technology.telecom.voip", "names": {"pl": "VoIP", "en": "VoIP", "de": "VoIP"}, "path": "/technologia/telekomunikacja/voip"},
                {"id": "technology.telecom.antennas", "names": {"pl": "Anteny i nadajniki", "en": "Antennas and transmitters", "de": "Antennen und Sender"}, "path": "/technologia/telekomunikacja/anteny_i_nadajniki"},
            ],
        },
        {
            "id": "technology.robotics",
            "names": {"pl": "Robotyka", "en": "Robotics", "de": "Robotik"},
            "path": "/technologia/robotyka",
            "subcategories": [
                {"id": "technology.robotics.industrial", "names": {"pl": "Roboty przemysłowe", "en": "Industrial robots", "de": "Industrieroboter"}, "path": "/technologia/robotyka/roboty_przemyslowe"},
                {"id": "technology.robotics.drones", "names": {"pl": "Drony", "en": "Drones", "de": "Drohnen"}, "path": "/technologia/robotyka/drony"},
                {"id": "technology.robotics.home", "names": {"pl": "Automatyka domowa", "en": "Home automation", "de": "Hausautomation"}, "path": "/technologia/robotyka/automatyka_domowa"},
                {"id": "technology.robotics.ai", "names": {"pl": "AI i ML", "en": "AI and ML", "de": "KI und ML"}, "path": "/technologia/robotyka/ai_i_ml"},
            ],
        },
        {
            "id": "technology.automotive",
            "names": {"pl": "Motoryzacja", "en": "Automotive", "de": "Kfz"},
            "path": "/technologia/motoryzacja",
            "subcategories": [
                {"id": "technology.automotive.cars", "names": {"pl": "Samochody osobowe", "en": "Passenger cars", "de": "Pkw"}, "path": "/technologia/motoryzacja/samochody_osobowe"},
                {"id": "technology.automotive.trucks", "names": {"pl": "Samochody ciężarowe", "en": "Trucks", "de": "Lkw"}, "path": "/technologia/motoryzacja/samochody_ciezarowe"},
                {"id": "technology.automotive.motorcycles", "names": {"pl": "Motocykle", "en": "Motorcycles", "de": "Motorräder"}, "path": "/technologia/motoryzacja/motocykle"},
                {"id": "technology.automotive.ev", "names": {"pl": "Elektryczne i hybrydy", "en": "Electric and hybrids", "de": "Elektro und Hybride"}, "path": "/technologia/motoryzacja/elektryczne_i_hybrydy"},
                {"id": "technology.automotive.service", "names": {"pl": "Naprawa i serwis", "en": "Repair and service", "de": "Reparatur und Service"}, "path": "/technologia/motoryzacja/naprawa_i_serwis"},
                {"id": "technology.automotive.license", "names": {"pl": "Prawo jazdy", "en": "Driving license", "de": "Führerschein"}, "path": "/technologia/motoryzacja/prawo_jazdy"},
            ],
        },
        {
            "id": "technology.aviation",
            "names": {"pl": "Lotnictwo", "en": "Aviation", "de": "Luftfahrt"},
            "path": "/technologia/lotnictwo",
            "subcategories": [
                {"id": "technology.aviation.avionics", "names": {"pl": "Awionika", "en": "Avionics", "de": "Avionik"}, "path": "/technologia/lotnictwo/awionika"},
                {"id": "technology.aviation.training", "names": {"pl": "Szkolenia pilotów", "en": "Pilot training", "de": "Pilotenausbildung"}, "path": "/technologia/lotnictwo/szkolenia_pilotow"},
                {"id": "technology.aviation.regulations", "names": {"pl": "Przepisy lotnicze", "en": "Aviation regulations", "de": "Luftfahrtvorschriften"}, "path": "/technologia/lotnictwo/przepisy_lotnicze"},
            ],
        },
        {
            "id": "technology.industry",
            "names": {"pl": "Przemysł", "en": "Industry", "de": "Industrie"},
            "path": "/technologia/przemysl",
            "subcategories": [
                {"id": "technology.industry.production", "names": {"pl": "Produkcja", "en": "Production", "de": "Produktion"}, "path": "/technologia/przemysl/produkcja"},
                {"id": "technology.industry.logistics", "names": {"pl": "Logistyka", "en": "Logistics", "de": "Logistik"}, "path": "/technologia/przemysl/logistyka"},
                {"id": "technology.industry.quality", "names": {"pl": "Jakość", "en": "Quality", "de": "Qualität"}, "path": "/technologia/przemysl/jakosc"},
                {"id": "technology.industry.safety", "names": {"pl": "Bezpieczeństwo przemysłowe", "en": "Industrial safety", "de": "Industriesicherheit"}, "path": "/technologia/przemysl/bezpieczenstwo_przemyslowe"},
            ],
        },
    ],
}

# ============================================================================
# 5. BUDOWNICTWO / CONSTRUCTION
# ============================================================================
CONSTRUCTION = {
    "id": "construction",
    "names": {"pl": "Budownictwo", "en": "Construction", "de": "Bauwesen"},
    "path": "/budownictwo",
    "path_hints": ["budownictwo", "budowlany", "construction", "building", "bauwesen", "bau",
                   "nieruchomosci", "nieruchomość", "real_estate"],
    "keywords": {
        "pl": ["budownictwo", "budynek", "konstrukcja", "beton", "fundament", "ściana",
               "dach", "instalacja", "architekt", "projekt", "pozwolenie", "nieruchomość",
               "mieszkanie", "dom", "remont", "budowa", "geodeta", "deweloper"],
        "en": ["construction", "building", "structure", "concrete", "foundation", "wall",
               "roof", "installation", "architect", "design", "permit", "real estate",
               "apartment", "house", "renovation", "development", "surveyor"],
        "de": ["bauwesen", "gebäude", "konstruktion", "beton", "fundament", "wand",
               "dach", "installation", "architekt", "entwurf", "baugenehmigung",
               "immobilien", "wohnung", "haus", "renovierung", "bauentwicklung"],
    },
    "subcategories": [
        {
            "id": "construction.design",
            "names": {"pl": "Projektowanie", "en": "Design", "de": "Planung"},
            "path": "/budownictwo/projektowanie",
            "subcategories": [
                {"id": "construction.design.architecture", "names": {"pl": "Architektura", "en": "Architecture", "de": "Architektur"}, "path": "/budownictwo/projektowanie/architektura"},
                {"id": "construction.design.installations", "names": {"pl": "Instalacje", "en": "Installations", "de": "Installationen"}, "path": "/budownictwo/projektowanie/instalacje"},
                {"id": "construction.design.structures", "names": {"pl": "Konstrukcje", "en": "Structures", "de": "Konstruktionen"}, "path": "/budownictwo/projektowanie/konstrukcje"},
                {"id": "construction.design.land", "names": {"pl": "Zagospodarowanie terenu", "en": "Land development", "de": "Flächennutzung"}, "path": "/budownictwo/projektowanie/zagospodarowanie_terenu"},
            ],
        },
        {
            "id": "construction.materials",
            "names": {"pl": "Materiały", "en": "Materials", "de": "Baumaterialien"},
            "path": "/budownictwo/materialy",
            "subcategories": [
                {"id": "construction.materials.concrete", "names": {"pl": "Beton i żelbet", "en": "Concrete and reinforced concrete", "de": "Beton und Stahlbeton"}, "path": "/budownictwo/materialy/beton_i_zelbet"},
                {"id": "construction.materials.wood", "names": {"pl": "Drewno", "en": "Wood", "de": "Holz"}, "path": "/budownictwo/materialy/drewno"},
                {"id": "construction.materials.steel", "names": {"pl": "Stal", "en": "Steel", "de": "Stahl"}, "path": "/budownictwo/materialy/stal"},
                {"id": "construction.materials.insulation", "names": {"pl": "Izolacje", "en": "Insulation", "de": "Dämmung"}, "path": "/budownictwo/materialy/izolacje"},
                {"id": "construction.materials.windows", "names": {"pl": "Okna i drzwi", "en": "Windows and doors", "de": "Fenster und Türen"}, "path": "/budownictwo/materialy/okna_i_drzwi"},
            ],
        },
        {
            "id": "construction.execution",
            "names": {"pl": "Wykonawstwo", "en": "Construction execution", "de": "Bauausführung"},
            "path": "/budownictwo/wykonawstwo",
            "subcategories": [
                {"id": "construction.execution.foundations", "names": {"pl": "Fundamenty", "en": "Foundations", "de": "Fundamente"}, "path": "/budownictwo/wykonawstwo/fundamenty"},
                {"id": "construction.execution.walls", "names": {"pl": "Ściany i stropy", "en": "Walls and ceilings", "de": "Wände und Decken"}, "path": "/budownictwo/wykonawstwo/sciany_i_stropy"},
                {"id": "construction.execution.roofs", "names": {"pl": "Dachy", "en": "Roofs", "de": "Dächer"}, "path": "/budownictwo/wykonawstwo/dachy"},
                {"id": "construction.execution.finishing", "names": {"pl": "Wykończenia", "en": "Finishing works", "de": "Ausbauarbeiten"}, "path": "/budownictwo/wykonawstwo/wykonczenia"},
                {"id": "construction.execution.sanitary", "names": {"pl": "Instalacje sanitarne", "en": "Sanitary installations", "de": "Sanitärinstallationen"}, "path": "/budownictwo/wykonawstwo/instalacje_sanitarne"},
            ],
        },
        {
            "id": "construction.systems",
            "names": {"pl": "Instalacje", "en": "Building systems", "de": "Gebäudetechnik"},
            "path": "/budownictwo/instalacje",
            "subcategories": [
                {"id": "construction.systems.electrical", "names": {"pl": "Elektryczne", "en": "Electrical", "de": "Elektroinstallationen"}, "path": "/budownictwo/instalacje/elektryczne"},
                {"id": "construction.systems.plumbing", "names": {"pl": "Wod-kan", "en": "Plumbing", "de": "Sanitär"}, "path": "/budownictwo/instalacje/wod_kan"},
                {"id": "construction.systems.heating", "names": {"pl": "Ogrzewanie", "en": "Heating", "de": "Heizung"}, "path": "/budownictwo/instalacje/ogrzewanie"},
                {"id": "construction.systems.ac", "names": {"pl": "Klimatyzacja", "en": "Air conditioning", "de": "Klimaanlage"}, "path": "/budownictwo/instalacje/klimatyzacja"},
                {"id": "construction.systems.ventilation", "names": {"pl": "Wentylacja", "en": "Ventilation", "de": "Lüftung"}, "path": "/budownictwo/instalacje/wentylacja"},
                {"id": "construction.systems.smarthome", "names": {"pl": "Inteligentny dom", "en": "Smart home", "de": "Smart Home"}, "path": "/budownictwo/instalacje/inteligentny_dom"},
            ],
        },
        {
            "id": "construction.law",
            "names": {"pl": "Prawo budowlane", "en": "Construction law", "de": "Baurecht"},
            "path": "/budownictwo/prawo_budowlane",
            "subcategories": [
                {"id": "construction.law.permits", "names": {"pl": "Pozwolenia", "en": "Permits", "de": "Baugenehmigungen"}, "path": "/budownictwo/prawo_budowlane/pozwolenia"},
                {"id": "construction.law.standards", "names": {"pl": "Normy i standardy", "en": "Standards and norms", "de": "Normen und Standards"}, "path": "/budownictwo/prawo_budowlane/normy_i_standardy"},
                {"id": "construction.law.supervision", "names": {"pl": "Nadzór budowlany", "en": "Building supervision", "de": "Bauaufsicht"}, "path": "/budownictwo/prawo_budowlane/nadzor_budowlany"},
            ],
        },
        {
            "id": "construction.real_estate",
            "names": {"pl": "Nieruchomości", "en": "Real estate", "de": "Immobilien"},
            "path": "/budownictwo/nieruchomosci",
            "subcategories": [
                {"id": "construction.real_estate.buy_sell", "names": {"pl": "Kupno i sprzedaż", "en": "Buying and selling", "de": "Kauf und Verkauf"}, "path": "/budownictwo/nieruchomosci/kupno_sprzedaz"},
                {"id": "construction.real_estate.rent", "names": {"pl": "Najem", "en": "Rental", "de": "Miete"}, "path": "/budownictwo/nieruchomosci/najem"},
                {"id": "construction.real_estate.land_registry", "names": {"pl": "Księgi wieczyste", "en": "Land registry", "de": "Grundbuch"}, "path": "/budownictwo/nieruchomosci/ksiegi_wieczyste"},
                {"id": "construction.real_estate.surveying", "names": {"pl": "Geodezja", "en": "Surveying", "de": "Vermessung"}, "path": "/budownictwo/nieruchomosci/geodezja"},
                {"id": "construction.real_estate.valuation", "names": {"pl": "Wycena", "en": "Valuation", "de": "Bewertung"}, "path": "/budownictwo/nieruchomosci/wycena"},
            ],
        },
    ],
}

# ============================================================================
# 6. EDUKACJA / EDUCATION
# ============================================================================
EDUCATION = {
    "id": "education",
    "names": {"pl": "Edukacja", "en": "Education", "de": "Bildung"},
    "path": "/edukacja",
    "path_hints": ["edukacja", "edukacyjny", "education", "educational", "bildung", "schule",
                   "nauka", "szkoła", "university", "studia"],
    "keywords": {
        "pl": ["edukacja", "szkoła", "nauka", "nauczyciel", "uczeń", "student",
               "kurs", "egzamin", "dyplom", "wykład", "podręcznik", "ocena",
               "matura", "studia", "język", "pedagogika", "szkolenie"],
        "en": ["education", "school", "learning", "teacher", "student", "pupil",
               "course", "exam", "diploma", "lecture", "textbook", "grade",
               "university", "language", "pedagogy", "training"],
        "de": ["bildung", "schule", "lernen", "lehrer", "schüler", "student",
               "kurs", "prüfung", "diplom", "vorlesung", "lehrbuch", "note",
               "universität", "sprache", "pädagogik", "ausbildung"],
    },
    "subcategories": [
        {
            "id": "education.school",
            "names": {"pl": "Szkolnictwo", "en": "Schooling", "de": "Schulbildung"},
            "path": "/edukacja/szkolnictwo",
            "subcategories": [
                {"id": "education.school.kindergarten", "names": {"pl": "Przedszkole", "en": "Kindergarten", "de": "Kindergarten"}, "path": "/edukacja/szkolnictwo/przedszkole"},
                {"id": "education.school.primary", "names": {"pl": "Podstawówka", "en": "Primary school", "de": "Grundschule"}, "path": "/edukacja/szkolnictwo/podstawowka"},
                {"id": "education.school.secondary", "names": {"pl": "Szkoła średnia", "en": "Secondary school", "de": "Weiterführende Schule"}, "path": "/edukacja/szkolnictwo/srednia"},
                {"id": "education.school.matura", "names": {"pl": "Matura", "en": "Matura/A-levels", "de": "Abitur"}, "path": "/edukacja/szkolnictwo/matura"},
                {"id": "education.school.special", "names": {"pl": "Szkoły specjalne", "en": "Special schools", "de": "Sonderschulen"}, "path": "/edukacja/szkolnictwo/szkoly_specjalne"},
            ],
        },
        {
            "id": "education.university",
            "names": {"pl": "Studia", "en": "University studies", "de": "Hochschulstudium"},
            "path": "/edukacja/studia",
            "subcategories": [
                {"id": "education.university.admission", "names": {"pl": "Rekrutacja", "en": "Admission", "de": "Zulassung"}, "path": "/edukacja/studia/rekrutacja"},
                {"id": "education.university.programs", "names": {"pl": "Programy studiów", "en": "Study programs", "de": "Studienprogramme"}, "path": "/edukacja/studia/programy_studiow"},
                {"id": "education.university.scholarships", "names": {"pl": "Stypendia", "en": "Scholarships", "de": "Stipendien"}, "path": "/edukacja/studia/stypendia"},
                {"id": "education.university.internships", "names": {"pl": "Praktyki", "en": "Internships", "de": "Praktika"}, "path": "/edukacja/studia/praktyki"},
                {"id": "education.university.thesis", "names": {"pl": "Prace dyplomowe", "en": "Theses", "de": "Abschlussarbeiten"}, "path": "/edukacja/studia/prace_dyplomowe"},
            ],
        },
        {
            "id": "education.languages",
            "names": {"pl": "Języki", "en": "Languages", "de": "Sprachen"},
            "path": "/edukacja/jezyki",
            "subcategories": [
                {"id": "education.languages.english", "names": {"pl": "Angielski", "en": "English", "de": "Englisch"}, "path": "/edukacja/jezyki/angielski"},
                {"id": "education.languages.german", "names": {"pl": "Niemiecki", "en": "German", "de": "Deutsch"}, "path": "/edukacja/jezyki/niemiecki"},
                {"id": "education.languages.spanish", "names": {"pl": "Hiszpański", "en": "Spanish", "de": "Spanisch"}, "path": "/edukacja/jezyki/hiszpanski"},
                {"id": "education.languages.french", "names": {"pl": "Francuski", "en": "French", "de": "Französisch"}, "path": "/edukacja/jezyki/francuski"},
                {"id": "education.languages.russian", "names": {"pl": "Rosyjski", "en": "Russian", "de": "Russisch"}, "path": "/edukacja/jezyki/rosyjski"},
                {"id": "education.languages.other", "names": {"pl": "Inne języki", "en": "Other languages", "de": "Andere Sprachen"}, "path": "/edukacja/jezyki/inne_jezyki"},
            ],
        },
        {
            "id": "education.training",
            "names": {"pl": "Szkolenia", "en": "Training", "de": "Schulungen"},
            "path": "/edukacja/szkolenia",
            "subcategories": [
                {"id": "education.training.vocational", "names": {"pl": "Zawodowe", "en": "Vocational", "de": "Berufsbildung"}, "path": "/edukacja/szkolenia/zawodowe"},
                {"id": "education.training.soft_skills", "names": {"pl": "Kompetencje miękkie", "en": "Soft skills", "de": "Soft Skills"}, "path": "/edukacja/szkolenia/kompetencji_miekkich"},
                {"id": "education.training.it", "names": {"pl": "IT i techniczne", "en": "IT and technical", "de": "IT und Technisch"}, "path": "/edukacja/szkolenia/it_i_techniczne"},
                {"id": "education.training.online", "names": {"pl": "Kursy online", "en": "Online courses", "de": "Online-Kurse"}, "path": "/edukacja/szkolenia/kursy_online"},
            ],
        },
        {
            "id": "education.science",
            "names": {"pl": "Nauka", "en": "Science", "de": "Wissenschaft"},
            "path": "/edukacja/nauka",
            "subcategories": [
                {"id": "education.science.math", "names": {"pl": "Matematyka", "en": "Mathematics", "de": "Mathematik"}, "path": "/edukacja/nauka/matematyka"},
                {"id": "education.science.physics", "names": {"pl": "Fizyka", "en": "Physics", "de": "Physik"}, "path": "/edukacja/nauka/fizyka"},
                {"id": "education.science.chemistry", "names": {"pl": "Chemia", "en": "Chemistry", "de": "Chemie"}, "path": "/edukacja/nauka/chemia"},
                {"id": "education.science.biology", "names": {"pl": "Biologia", "en": "Biology", "de": "Biologie"}, "path": "/edukacja/nauka/biologia"},
                {"id": "education.science.history", "names": {"pl": "Historia", "en": "History", "de": "Geschichte"}, "path": "/edukacja/nauka/historia"},
                {"id": "education.science.geography", "names": {"pl": "Geografia", "en": "Geography", "de": "Geographie"}, "path": "/edukacja/nauka/geografia"},
                {"id": "education.science.literature", "names": {"pl": "Literatura", "en": "Literature", "de": "Literatur"}, "path": "/edukacja/nauka/literatura"},
            ],
        },
    ],
}

# ============================================================================
# 7. ROLNICTWO / AGRICULTURE
# ============================================================================
AGRICULTURE = {
    "id": "agriculture",
    "names": {"pl": "Rolnictwo", "en": "Agriculture", "de": "Landwirtschaft"},
    "path": "/rolnictwo",
    "path_hints": ["rolnictwo", "rolniczy", "agriculture", "agricultural", "landwirtschaft",
                   "farming", "uprawy", "hodowla", "lesnictwo"],
    "keywords": {
        "pl": ["rolnictwo", "uprawa", "hodowla", "pole", "zboże", "warzywa",
               "owoce", "gleba", "nawóz", "ciągnik", "kombajn", "żniwa",
               "pastwisko", "bydło", "trzoda", "drób", "pszczelarstwo", "leśnictwo"],
        "en": ["agriculture", "farming", "cultivation", "livestock", "field", "grain",
               "vegetables", "fruits", "soil", "fertilizer", "tractor", "harvest",
               "cattle", "poultry", "apiculture", "forestry"],
        "de": ["landwirtschaft", "anbau", "tierhaltung", "feld", "getreide", "gemüse",
               "obst", "boden", "dünger", "traktor", "ernte", "rind", "geflügel",
               "imkerei", "forstwirtschaft"],
    },
    "subcategories": [
        {
            "id": "agriculture.crops",
            "names": {"pl": "Uprawa", "en": "Crop cultivation", "de": "Ackerbau"},
            "path": "/rolnictwo/uprawa",
            "subcategories": [
                {"id": "agriculture.crops.grains", "names": {"pl": "Zboża", "en": "Grains", "de": "Getreide"}, "path": "/rolnictwo/uprawa/zboza"},
                {"id": "agriculture.crops.vegetables", "names": {"pl": "Warzywa", "en": "Vegetables", "de": "Gemüse"}, "path": "/rolnictwo/uprawa/warzywa"},
                {"id": "agriculture.crops.fruits", "names": {"pl": "Owoce", "en": "Fruits", "de": "Obst"}, "path": "/rolnictwo/uprawa/owoce"},
                {"id": "agriculture.crops.oilseeds", "names": {"pl": "Rośliny oleiste", "en": "Oilseeds", "de": "Ölsaaten"}, "path": "/rolnictwo/uprawa/rosliny_oleiste"},
                {"id": "agriculture.crops.ornamental", "names": {"pl": "Rośliny ozdobne", "en": "Ornamental plants", "de": "Zierpflanzen"}, "path": "/rolnictwo/uprawa/rosliny_ozdobne"},
            ],
        },
        {
            "id": "agriculture.livestock",
            "names": {"pl": "Hodowla", "en": "Livestock farming", "de": "Tierhaltung"},
            "path": "/rolnictwo/hodowla",
            "subcategories": [
                {"id": "agriculture.livestock.cattle", "names": {"pl": "Bydło", "en": "Cattle", "de": "Rinderhaltung"}, "path": "/rolnictwo/hodowla/bydlo"},
                {"id": "agriculture.livestock.pigs", "names": {"pl": "Trzoda chlewna", "en": "Pigs", "de": "Schweinehaltung"}, "path": "/rolnictwo/hodowla/trzoda_chlewna"},
                {"id": "agriculture.livestock.poultry", "names": {"pl": "Drób", "en": "Poultry", "de": "Geflügelhaltung"}, "path": "/rolnictwo/hodowla/drob"},
                {"id": "agriculture.livestock.sheep", "names": {"pl": "Owce i kozy", "en": "Sheep and goats", "de": "Schafe und Ziegen"}, "path": "/rolnictwo/hodowla/owce_i_kozy"},
                {"id": "agriculture.livestock.bees", "names": {"pl": "Pszczoły", "en": "Bees", "de": "Bienen"}, "path": "/rolnictwo/hodowla/pszczoly"},
            ],
        },
        {
            "id": "agriculture.machinery",
            "names": {"pl": "Maszyny rolnicze", "en": "Agricultural machinery", "de": "Landmaschinen"},
            "path": "/rolnictwo/maszyny_rolnicze",
            "subcategories": [
                {"id": "agriculture.machinery.tractors", "names": {"pl": "Ciągniki", "en": "Tractors", "de": "Traktoren"}, "path": "/rolnictwo/maszyny_rolnicze/ciagniki"},
                {"id": "agriculture.machinery.combines", "names": {"pl": "Kombajny", "en": "Combines", "de": "Mähdrescher"}, "path": "/rolnictwo/maszyny_rolnicze/kombajny"},
                {"id": "agriculture.machinery.fertilizing", "names": {"pl": "Maszyny do nawożenia", "en": "Fertilizing machinery", "de": "Düngermaschinen"}, "path": "/rolnictwo/maszyny_rolnicze/maszyny_do_nawozenia"},
                {"id": "agriculture.machinery.service", "names": {"pl": "Serwis i naprawa", "en": "Service and repair", "de": "Service und Reparatur"}, "path": "/rolnictwo/maszyny_rolnicze/serwis_i_naprawa"},
            ],
        },
        {
            "id": "agriculture.plant_protection",
            "names": {"pl": "Ochrona roślin", "en": "Plant protection", "de": "Pflanzenschutz"},
            "path": "/rolnictwo/ochrona_roslin",
            "subcategories": [
                {"id": "agriculture.plant_protection.diseases", "names": {"pl": "Choroby", "en": "Plant diseases", "de": "Pflanzenkrankheiten"}, "path": "/rolnictwo/ochrona_roslin/choroby"},
                {"id": "agriculture.plant_protection.pests", "names": {"pl": "Szkodniki", "en": "Pests", "de": "Schädlinge"}, "path": "/rolnictwo/ochrona_roslin/szkodniki"},
                {"id": "agriculture.plant_protection.fertilizers", "names": {"pl": "Nawozy", "en": "Fertilizers", "de": "Düngemittel"}, "path": "/rolnictwo/ochrona_roslin/nawozy"},
                {"id": "agriculture.plant_protection.pesticides", "names": {"pl": "Środki ochrony", "en": "Pesticides", "de": "Pestizide"}, "path": "/rolnictwo/ochrona_roslin/srodki_ochrony"},
            ],
        },
        {
            "id": "agriculture.forestry",
            "names": {"pl": "Leśnictwo", "en": "Forestry", "de": "Forstwirtschaft"},
            "path": "/rolnictwo/lesnictwo",
            "subcategories": [
                {"id": "agriculture.forestry.management", "names": {"pl": "Gospodarka leśna", "en": "Forest management", "de": "Forstwirtschaft"}, "path": "/rolnictwo/lesnictwo/gospodarka_lesna"},
                {"id": "agriculture.forestry.protection", "names": {"pl": "Ochrona lasu", "en": "Forest protection", "de": "Waldschutz"}, "path": "/rolnictwo/lesnictwo/ochrona_lasu"},
                {"id": "agriculture.forestry.timber", "names": {"pl": "Pozyskiwanie drewna", "en": "Timber harvesting", "de": "Holzeinschlag"}, "path": "/rolnictwo/lesnictwo/pozyskiwanie_drewna"},
                {"id": "agriculture.forestry.hunting", "names": {"pl": "Myślistwo", "en": "Hunting", "de": "Jagd"}, "path": "/rolnictwo/lesnictwo/mylistwo"},
            ],
        },
    ],
}

# ============================================================================
# 8. SPOŁECZEŃSTWO / SOCIETY
# ============================================================================
SOCIETY = {
    "id": "society",
    "names": {"pl": "Społeczeństwo", "en": "Society", "de": "Gesellschaft"},
    "path": "/spoleczenstwo",
    "path_hints": ["spoleczenstwo", "spoleczny", "society", "social", "gesellschaft",
                   "administracja", "wojsko", "policja", "konstytucja"],
    "keywords": {
        "pl": ["społeczeństwo", "obywatel", "administracja", "urząd", "konstytucja",
               "prawa człowieka", "wojsko", "policja", "straż", "organizacja",
               "fundacja", "wolontariat", "demokracja", "wybory", "mandat"],
        "en": ["society", "citizen", "administration", "office", "constitution",
               "human rights", "military", "police", "organization", "foundation",
               "volunteering", "democracy", "elections"],
        "de": ["gesellschaft", "bürger", "verwaltung", "amt", "verfassung",
               "menschenrechte", "militär", "polizei", "organisation", "stiftung",
               "ehrenamt", "demokratie", "wahlen"],
    },
    "subcategories": [
        {
            "id": "society.constitution",
            "names": {"pl": "Konstytucja", "en": "Constitution", "de": "Verfassung"},
            "path": "/spoleczenstwo/konstytucja",
            "subcategories": [
                {"id": "society.constitution.human_rights", "names": {"pl": "Prawa człowieka", "en": "Human rights", "de": "Menschenrechte"}, "path": "/spoleczenstwo/konstytucja/prawa_czlowieka"},
                {"id": "society.constitution.freedoms", "names": {"pl": "Wolności i obowiązki", "en": "Freedoms and duties", "de": "Freiheiten und Pflichten"}, "path": "/spoleczenstwo/konstytucja/wolnosci_i_obowiazki"},
                {"id": "society.constitution.state_bodies", "names": {"pl": "Organy państwowe", "en": "State bodies", "de": "Staatsorgane"}, "path": "/spoleczenstwo/konstytucja/organy_panstwowe"},
                {"id": "society.constitution.electoral", "names": {"pl": "Prawo wyborcze", "en": "Electoral law", "de": "Wahlrecht"}, "path": "/spoleczenstwo/konstytucja/prawo_wyborcze"},
            ],
        },
        {
            "id": "society.administration",
            "names": {"pl": "Administracja", "en": "Administration", "de": "Verwaltung"},
            "path": "/spoleczenstwo/administracja",
            "subcategories": [
                {"id": "society.administration.offices", "names": {"pl": "Urzędy", "en": "Government offices", "de": "Behörden"}, "path": "/spoleczenstwo/administracja/urzedy"},
                {"id": "society.administration.procedures", "names": {"pl": "Procedury", "en": "Procedures", "de": "Verfahren"}, "path": "/spoleczenstwo/administracja/procedury"},
                {"id": "society.administration.documents", "names": {"pl": "Dokumenty tożsamości", "en": "Identity documents", "de": "Ausweisdokumente"}, "path": "/spoleczenstwo/administracja/dokumenty_tozsamosci"},
                {"id": "society.administration.complaints", "names": {"pl": "Skargi i wnioski", "en": "Complaints and applications", "de": "Beschwerden und Anträge"}, "path": "/spoleczenstwo/administracja/skargi_i_wnioski"},
            ],
        },
        {
            "id": "society.military",
            "names": {"pl": "Wojsko", "en": "Military", "de": "Militär"},
            "path": "/spoleczenstwo/wojsko",
            "subcategories": [
                {"id": "society.military.service", "names": {"pl": "Służba wojskowa", "en": "Military service", "de": "Militärdienst"}, "path": "/spoleczenstwo/wojsko/sluzba_wojskowa"},
                {"id": "society.military.equipment", "names": {"pl": "Sprzęt wojskowy", "en": "Military equipment", "de": "Militärausrüstung"}, "path": "/spoleczenstwo/wojsko/sprzet_wojskowy"},
                {"id": "society.military.law", "names": {"pl": "Prawo wojenne", "en": "Law of war", "de": "Kriegsrecht"}, "path": "/spoleczenstwo/wojsko/prawo_wojenne"},
            ],
        },
        {
            "id": "society.police",
            "names": {"pl": "Policja i straż", "en": "Police and fire", "de": "Polizei und Feuerwehr"},
            "path": "/spoleczenstwo/policja_i_straz",
            "subcategories": [
                {"id": "society.police.powers", "names": {"pl": "Uprawnienia", "en": "Powers", "de": "Befugnisse"}, "path": "/spoleczenstwo/policja_i_straz/uprawnienia"},
                {"id": "society.police.interventions", "names": {"pl": "Interwencje", "en": "Interventions", "de": "Einsätze"}, "path": "/spoleczenstwo/policja_i_straz/interwencje"},
                {"id": "society.police.fines", "names": {"pl": "Mandaty", "en": "Fines", "de": "Bußgelder"}, "path": "/spoleczenstwo/policja_i_straz/mandaty"},
                {"id": "society.police.reports", "names": {"pl": "Zgłoszenia", "en": "Reports", "de": "Meldungen"}, "path": "/spoleczenstwo/policja_i_straz/zgloszenia"},
            ],
        },
        {
            "id": "society.ngo",
            "names": {"pl": "Organizacje pozarządowe", "en": "Non-governmental organizations", "de": "Nichtregierungsorganisationen"},
            "path": "/spoleczenstwo/organizacje_pozarzadowe",
            "subcategories": [
                {"id": "society.ngo.foundations", "names": {"pl": "Fundacje", "en": "Foundations", "de": "Stiftungen"}, "path": "/spoleczenstwo/organizacje_pozarzadowe/fundacje"},
                {"id": "society.ngo.associations", "names": {"pl": "Stowarzyszenia", "en": "Associations", "de": "Vereine"}, "path": "/spoleczenstwo/organizacje_pozarzadowe/stowarzyszenia"},
                {"id": "society.ngo.volunteering", "names": {"pl": "Wolontariat", "en": "Volunteering", "de": "Ehrenamt"}, "path": "/spoleczenstwo/organizacje_pozarzadowe/wolontariat"},
            ],
        },
    ],
}

# ============================================================================
# 9. KULTURA I ROZRYWKA / CULTURE
# ============================================================================
CULTURE = {
    "id": "culture",
    "names": {"pl": "Kultura i rozrywka", "en": "Culture and entertainment", "de": "Kultur und Unterhaltung"},
    "path": "/kultura_i_rozrywka",
    "path_hints": ["kultura", "rozrywka", "kultura_i_rozrywka", "culture", "entertainment",
                   "kultur", "unterhaltung", "sztuka", "muzyka", "film", "literatura"],
    "keywords": {
        "pl": ["kultura", "sztuka", "muzyka", "film", "teatr", "literatura", "gry",
               "turystyka", "artysta", "koncert", "galeria", "muzeum", "spektakl",
               "książka", "fotografia", "malarstwo", "reżyser", "aktor"],
        "en": ["culture", "art", "music", "film", "theatre", "literature", "games",
               "tourism", "artist", "concert", "gallery", "museum", "performance",
               "book", "photography", "painting", "director", "actor"],
        "de": ["kultur", "kunst", "musik", "film", "theater", "literatur", "spiele",
               "tourismus", "künstler", "konzert", "galerie", "museum", "aufführung",
               "buch", "fotografie", "malerei", "regisseur", "schauspieler"],
    },
    "subcategories": [
        {
            "id": "culture.art",
            "names": {"pl": "Sztuka", "en": "Art", "de": "Kunst"},
            "path": "/kultura_i_rozrywka/sztuka",
            "subcategories": [
                {"id": "culture.art.painting", "names": {"pl": "Malarstwo", "en": "Painting", "de": "Malerei"}, "path": "/kultura_i_rozrywka/sztuka/malarstwo"},
                {"id": "culture.art.sculpture", "names": {"pl": "Rzeźba", "en": "Sculpture", "de": "Skulptur"}, "path": "/kultura_i_rozrywka/sztuka/rzezba"},
                {"id": "culture.art.photography", "names": {"pl": "Fotografia", "en": "Photography", "de": "Fotografie"}, "path": "/kultura_i_rozrywka/sztuka/fotografia"},
                {"id": "culture.art.museums", "names": {"pl": "Muzea i galerie", "en": "Museums and galleries", "de": "Museen und Galerien"}, "path": "/kultura_i_rozrywka/sztuka/muzea_i_galerie"},
            ],
        },
        {
            "id": "culture.music",
            "names": {"pl": "Muzyka", "en": "Music", "de": "Musik"},
            "path": "/kultura_i_rozrywka/muzyka",
            "subcategories": [
                {"id": "culture.music.theory", "names": {"pl": "Teoria muzyki", "en": "Music theory", "de": "Musiktheorie"}, "path": "/kultura_i_rozrywka/muzyka/teoria_muzyki"},
                {"id": "culture.music.instruments", "names": {"pl": "Instrumenty", "en": "Instruments", "de": "Instrumente"}, "path": "/kultura_i_rozrywka/muzyka/instrumenty"},
                {"id": "culture.music.genres", "names": {"pl": "Gatunki", "en": "Genres", "de": "Genres"}, "path": "/kultura_i_rozrywka/muzyka/gatunki"},
                {"id": "culture.music.production", "names": {"pl": "Produkcja muzyczna", "en": "Music production", "de": "Musikproduktion"}, "path": "/kultura_i_rozrywka/muzyka/produkcja_muzyczna"},
            ],
        },
        {
            "id": "culture.film",
            "names": {"pl": "Film i teatr", "en": "Film and theatre", "de": "Film und Theater"},
            "path": "/kultura_i_rozrywka/film_i_teatr",
            "subcategories": [
                {"id": "culture.film.production", "names": {"pl": "Produkcja filmowa", "en": "Film production", "de": "Filmproduktion"}, "path": "/kultura_i_rozrywka/film_i_teatr/produkcja_filmowa"},
                {"id": "culture.film.acting", "names": {"pl": "Aktorstwo", "en": "Acting", "de": "Schauspielkunst"}, "path": "/kultura_i_rozrywka/film_i_teatr/aktorstwo"},
                {"id": "culture.film.directing", "names": {"pl": "Reżyseria", "en": "Directing", "de": "Regie"}, "path": "/kultura_i_rozrywka/film_i_teatr/rezyseria"},
                {"id": "culture.film.theatre", "names": {"pl": "Teatr", "en": "Theatre", "de": "Theater"}, "path": "/kultura_i_rozrywka/film_i_teatr/teatr"},
            ],
        },
        {
            "id": "culture.literature",
            "names": {"pl": "Literatura", "en": "Literature", "de": "Literatur"},
            "path": "/kultura_i_rozrywka/literatura",
            "subcategories": [
                {"id": "culture.literature.prose", "names": {"pl": "Proza", "en": "Prose", "de": "Prosa"}, "path": "/kultura_i_rozrywka/literatura/proza"},
                {"id": "culture.literature.poetry", "names": {"pl": "Poezja", "en": "Poetry", "de": "Lyrik"}, "path": "/kultura_i_rozrywka/literatura/poezja"},
                {"id": "culture.literature.criticism", "names": {"pl": "Krytyka literacka", "en": "Literary criticism", "de": "Literaturkritik"}, "path": "/kultura_i_rozrywka/literatura/krytyka_literacka"},
            ],
        },
        {
            "id": "culture.games",
            "names": {"pl": "Gry", "en": "Games", "de": "Spiele"},
            "path": "/kultura_i_rozrywka/gry",
            "subcategories": [
                {"id": "culture.games.board", "names": {"pl": "Gry planszowe", "en": "Board games", "de": "Brettspiele"}, "path": "/kultura_i_rozrywka/gry/gry_planszowe"},
                {"id": "culture.games.video", "names": {"pl": "Gry komputerowe", "en": "Video games", "de": "Videospiele"}, "path": "/kultura_i_rozrywka/gry/gry_komputerowe"},
                {"id": "culture.games.card", "names": {"pl": "Gry karciane", "en": "Card games", "de": "Kartenspiele"}, "path": "/kultura_i_rozrywka/gry/gry_karciane"},
                {"id": "culture.games.esport", "names": {"pl": "Esport", "en": "Esport", "de": "E-Sport"}, "path": "/kultura_i_rozrywka/gry/esport"},
            ],
        },
        {
            "id": "culture.tourism",
            "names": {"pl": "Turystyka", "en": "Tourism", "de": "Tourismus"},
            "path": "/kultura_i_rozrywka/turystyka",
            "subcategories": [
                {"id": "culture.tourism.domestic", "names": {"pl": "Podróże krajowe", "en": "Domestic travel", "de": "Inlandsreisen"}, "path": "/kultura_i_rozrywka/turystyka/podroze_krajowe"},
                {"id": "culture.tourism.international", "names": {"pl": "Podróże zagraniczne", "en": "International travel", "de": "Auslandsreisen"}, "path": "/kultura_i_rozrywka/turystyka/podroze_zagraniczne"},
                {"id": "culture.tourism.accommodation", "names": {"pl": "Noclegi", "en": "Accommodation", "de": "Unterkünfte"}, "path": "/kultura_i_rozrywka/turystyka/noclegi"},
                {"id": "culture.tourism.guides", "names": {"pl": "Przewodniki", "en": "Travel guides", "de": "Reiseführer"}, "path": "/kultura_i_rozrywka/turystyka/przewodniki"},
            ],
        },
    ],
}

# ============================================================================
# 10. SPORT
# ============================================================================
SPORT = {
    "id": "sport",
    "names": {"pl": "Sport", "en": "Sport", "de": "Sport"},
    "path": "/sport",
    "path_hints": ["sport", "sportowy", "sports", "athletic", "sportlich", "piłka", "fitness",
                   "rekreacja", "trening", "zawody"],
    "keywords": {
        "pl": ["sport", "zawody", "trening", "drużyna", "gracz", "sportowiec",
               "piłka", "bieg", "pływanie", "jazda", "walka", "turniej", "liga",
               "mistrzostwo", "olimpiada", "fitness", "siłownia", "rekreacja"],
        "en": ["sport", "competition", "training", "team", "player", "athlete",
               "ball", "running", "swimming", "cycling", "fighting", "tournament",
               "league", "championship", "olympics", "fitness", "gym", "recreation"],
        "de": ["sport", "wettkampf", "training", "mannschaft", "spieler", "sportler",
               "ball", "laufen", "schwimmen", "radfahren", "kampf", "turnier",
               "liga", "meisterschaft", "olympia", "fitness", "gym", "freizeit"],
    },
    "subcategories": [
        {
            "id": "sport.football",
            "names": {"pl": "Piłka nożna", "en": "Football", "de": "Fußball"},
            "path": "/sport/pilka_nozna",
            "subcategories": [
                {"id": "sport.football.technique", "names": {"pl": "Technika", "en": "Technique", "de": "Technik"}, "path": "/sport/pilka_nozna/technika"},
                {"id": "sport.football.tactics", "names": {"pl": "Taktyka", "en": "Tactics", "de": "Taktik"}, "path": "/sport/pilka_nozna/taktyka"},
                {"id": "sport.football.training", "names": {"pl": "Trening", "en": "Training", "de": "Training"}, "path": "/sport/pilka_nozna/trening"},
                {"id": "sport.football.rules", "names": {"pl": "Przepisy", "en": "Rules", "de": "Regeln"}, "path": "/sport/pilka_nozna/przepisy"},
            ],
        },
        {
            "id": "sport.water",
            "names": {"pl": "Sporty wodne", "en": "Water sports", "de": "Wassersport"},
            "path": "/sport/sporty_wodne",
            "subcategories": [
                {"id": "sport.water.swimming", "names": {"pl": "Pływanie", "en": "Swimming", "de": "Schwimmen"}, "path": "/sport/sporty_wodne/plywanie"},
                {"id": "sport.water.sailing", "names": {"pl": "Żeglarstwo", "en": "Sailing", "de": "Segeln"}, "path": "/sport/sporty_wodne/zeglajstwo"},
                {"id": "sport.water.kayaking", "names": {"pl": "Kajakarstwo", "en": "Kayaking", "de": "Kajak"}, "path": "/sport/sporty_wodne/kajakarstwo"},
            ],
        },
        {
            "id": "sport.winter",
            "names": {"pl": "Sporty zimowe", "en": "Winter sports", "de": "Wintersport"},
            "path": "/sport/sporty_zimowe",
            "subcategories": [
                {"id": "sport.winter.skiing", "names": {"pl": "Narciarstwo", "en": "Skiing", "de": "Skifahren"}, "path": "/sport/sporty_zimowe/narciarstwo"},
                {"id": "sport.winter.snowboard", "names": {"pl": "Snowboard", "en": "Snowboard", "de": "Snowboard"}, "path": "/sport/sporty_zimowe/snowboard"},
                {"id": "sport.winter.skating", "names": {"pl": "Łyżwiarstwo", "en": "Skating", "de": "Eislaufen"}, "path": "/sport/sporty_zimowe/lyzwiarstwo"},
                {"id": "sport.winter.hockey", "names": {"pl": "Hokej", "en": "Hockey", "de": "Eishockey"}, "path": "/sport/sporty_zimowe/hokej"},
            ],
        },
        {
            "id": "sport.combat",
            "names": {"pl": "Sporty walki", "en": "Combat sports", "de": "Kampfsport"},
            "path": "/sport/sporty_walki",
            "subcategories": [
                {"id": "sport.combat.boxing", "names": {"pl": "Boks", "en": "Boxing", "de": "Boxen"}, "path": "/sport/sporty_walki/boks"},
                {"id": "sport.combat.karate", "names": {"pl": "Karate", "en": "Karate", "de": "Karate"}, "path": "/sport/sporty_walki/karate"},
                {"id": "sport.combat.judo", "names": {"pl": "Judo", "en": "Judo", "de": "Judo"}, "path": "/sport/sporty_walki/judo"},
                {"id": "sport.combat.mma", "names": {"pl": "MMA", "en": "MMA", "de": "MMA"}, "path": "/sport/sporty_walki/mma"},
            ],
        },
        {
            "id": "sport.strength",
            "names": {"pl": "Sporty siłowe", "en": "Strength sports", "de": "Kraftsport"},
            "path": "/sport/sporty_silowe",
            "subcategories": [
                {"id": "sport.strength.bodybuilding", "names": {"pl": "Kulturystyka", "en": "Bodybuilding", "de": "Bodybuilding"}, "path": "/sport/sporty_silowe/kulturystyka"},
                {"id": "sport.strength.powerlifting", "names": {"pl": "Trójbój", "en": "Powerlifting", "de": "Powerlifting"}, "path": "/sport/sporty_silowe/trojboj"},
                {"id": "sport.strength.crossfit", "names": {"pl": "CrossFit", "en": "CrossFit", "de": "CrossFit"}, "path": "/sport/sporty_silowe/crossfit"},
            ],
        },
        {
            "id": "sport.recreation",
            "names": {"pl": "Rekreacja", "en": "Recreation", "de": "Freizeitaktivitäten"},
            "path": "/sport/rekreacja",
            "subcategories": [
                {"id": "sport.recreation.running", "names": {"pl": "Bieganie", "en": "Running", "de": "Laufen"}, "path": "/sport/rekreacja/bieganie"},
                {"id": "sport.recreation.cycling", "names": {"pl": "Rower", "en": "Cycling", "de": "Radfahren"}, "path": "/sport/rekreacja/rower"},
                {"id": "sport.recreation.hiking", "names": {"pl": "Turystyka górska", "en": "Hiking", "de": "Wandern"}, "path": "/sport/rekreacja/turystyka_gorska"},
                {"id": "sport.recreation.nordic_walking", "names": {"pl": "Nordic walking", "en": "Nordic walking", "de": "Nordic Walking"}, "path": "/sport/rekreacja/nordic_walking"},
            ],
        },
    ],
}

# ============================================================================
# 11. RODZINA I DOM / FAMILY
# ============================================================================
FAMILY = {
    "id": "family",
    "names": {"pl": "Rodzina i dom", "en": "Family and home", "de": "Familie und Haus"},
    "path": "/rodzina_i_dom",
    "path_hints": ["rodzina", "rodzina_i_dom", "family", "home", "familie", "haushalt",
                   "dom", "dzieci", "malzenstwo", "seniorzy"],
    "keywords": {
        "pl": ["rodzina", "dom", "małżeństwo", "dzieci", "wychowanie", "seniorzy",
               "emeryt", "gotowanie", "sprzątanie", "zwierzęta domowe", "pies", "kot",
               "mieszkanie", "domowe", "zasiłek", "świadczenie", "opieka"],
        "en": ["family", "home", "marriage", "children", "parenting", "elderly",
               "retirement", "cooking", "cleaning", "pets", "dog", "cat",
               "apartment", "household", "benefit", "care"],
        "de": ["familie", "haus", "ehe", "kinder", "erziehung", "senioren",
               "rente", "kochen", "putzen", "haustiere", "hund", "katze",
               "wohnung", "haushalt", "leistung", "pflege"],
    },
    "subcategories": [
        {
            "id": "family.marriage",
            "names": {"pl": "Małżeństwo", "en": "Marriage", "de": "Ehe"},
            "path": "/rodzina_i_dom/malzenstwo",
            "subcategories": [
                {"id": "family.marriage.legal", "names": {"pl": "Prawne aspekty", "en": "Legal aspects", "de": "Rechtliche Aspekte"}, "path": "/rodzina_i_dom/malzenstwo/prawne_aspekty"},
                {"id": "family.marriage.property", "names": {"pl": "Własność", "en": "Property", "de": "Eigentum"}, "path": "/rodzina_i_dom/malzenstwo/wlasnosc"},
                {"id": "family.marriage.divorce", "names": {"pl": "Rozwód i rozłąka", "en": "Divorce and separation", "de": "Scheidung und Trennung"}, "path": "/rodzina_i_dom/malzenstwo/rozwod_i_rozluka"},
            ],
        },
        {
            "id": "family.children",
            "names": {"pl": "Dzieci", "en": "Children", "de": "Kinder"},
            "path": "/rodzina_i_dom/dzieci",
            "subcategories": [
                {"id": "family.children.parenting", "names": {"pl": "Wychowanie", "en": "Parenting", "de": "Erziehung"}, "path": "/rodzina_i_dom/dzieci/wychowanie"},
                {"id": "family.children.health", "names": {"pl": "Zdrowie dzieci", "en": "Children's health", "de": "Kindergesundheit"}, "path": "/rodzina_i_dom/dzieci/zdrowie_dzieci"},
                {"id": "family.children.benefits", "names": {"pl": "Zasiłki i świadczenia", "en": "Benefits and allowances", "de": "Leistungen und Beihilfen"}, "path": "/rodzina_i_dom/dzieci/zasilki_i_swiadczenia"},
                {"id": "family.children.rights", "names": {"pl": "Prawa dziecka", "en": "Children's rights", "de": "Kinderrechte"}, "path": "/rodzina_i_dom/dzieci/prawa_dziecka"},
            ],
        },
        {
            "id": "family.elderly",
            "names": {"pl": "Seniorzy", "en": "Elderly", "de": "Senioren"},
            "path": "/rodzina_i_dom/seniorzy",
            "subcategories": [
                {"id": "family.elderly.pension", "names": {"pl": "Emerytury", "en": "Pensions", "de": "Renten"}, "path": "/rodzina_i_dom/seniorzy/emerytury"},
                {"id": "family.elderly.care", "names": {"pl": "Opieka", "en": "Care", "de": "Pflege"}, "path": "/rodzina_i_dom/seniorzy/opieka"},
                {"id": "family.elderly.health", "names": {"pl": "Zdrowie seniora", "en": "Senior health", "de": "Seniorengesundheit"}, "path": "/rodzina_i_dom/seniorzy/zdrowie_seniora"},
                {"id": "family.elderly.activation", "names": {"pl": "Aktywizacja", "en": "Activation", "de": "Aktivierung"}, "path": "/rodzina_i_dom/seniorzy/aktywizacja"},
            ],
        },
        {
            "id": "family.household",
            "names": {"pl": "Gospodarstwo domowe", "en": "Household", "de": "Haushalt"},
            "path": "/rodzina_i_dom/gospodarstwo_domowe",
            "subcategories": [
                {"id": "family.household.cleaning", "names": {"pl": "Sprzątanie", "en": "Cleaning", "de": "Reinigung"}, "path": "/rodzina_i_dom/gospodarstwo_domowe/sprzatanie"},
                {"id": "family.household.cooking", "names": {"pl": "Gotowanie", "en": "Cooking", "de": "Kochen"}, "path": "/rodzina_i_dom/gospodarstwo_domowe/gotowanie"},
                {"id": "family.household.organization", "names": {"pl": "Organizacja", "en": "Organization", "de": "Organisation"}, "path": "/rodzina_i_dom/gospodarstwo_domowe/organizacja"},
            ],
        },
        {
            "id": "family.pets",
            "names": {"pl": "Zwierzęta domowe", "en": "Pets", "de": "Haustiere"},
            "path": "/rodzina_i_dom/zwierzeta_domowe",
            "subcategories": [
                {"id": "family.pets.dogs", "names": {"pl": "Psy", "en": "Dogs", "de": "Hunde"}, "path": "/rodzina_i_dom/zwierzeta_domowe/psy"},
                {"id": "family.pets.cats", "names": {"pl": "Koty", "en": "Cats", "de": "Katzen"}, "path": "/rodzina_i_dom/zwierzeta_domowe/koty"},
                {"id": "family.pets.birds", "names": {"pl": "Ptaki", "en": "Birds", "de": "Vögel"}, "path": "/rodzina_i_dom/zwierzeta_domowe/ptaki"},
                {"id": "family.pets.fish", "names": {"pl": "Rybki", "en": "Fish", "de": "Fische"}, "path": "/rodzina_i_dom/zwierzeta_domowe/rybki"},
            ],
        },
    ],
}

# ============================================================================
# 12. RELIGIA I FILOZOFIA / RELIGION
# ============================================================================
RELIGION = {
    "id": "religion",
    "names": {"pl": "Religia i filozofia", "en": "Religion and philosophy", "de": "Religion und Philosophie"},
    "path": "/religia_i_filozofia",
    "path_hints": ["religia", "religia_i_filozofia", "religion", "philosophy", "philosophie",
                   "filozofia", "duchowość", "kościół", "church"],
    "keywords": {
        "pl": ["religia", "filozofia", "wiara", "bóg", "kościół", "modlitwa",
               "duchowość", "etyka", "moralność", "teologia", "liturgia", "sakrament",
               "medytacja", "buddyzm", "islam", "judaizm", "chrześcijaństwo"],
        "en": ["religion", "philosophy", "faith", "god", "church", "prayer",
               "spirituality", "ethics", "morality", "theology", "liturgy", "sacrament",
               "meditation", "buddhism", "islam", "judaism", "christianity"],
        "de": ["religion", "philosophie", "glaube", "gott", "kirche", "gebet",
               "spiritualität", "ethik", "moral", "theologie", "liturgie", "sakrament",
               "meditation", "buddhismus", "islam", "judentum", "christentum"],
    },
    "subcategories": [
        {
            "id": "religion.christianity",
            "names": {"pl": "Chrześcijaństwo", "en": "Christianity", "de": "Christentum"},
            "path": "/religia_i_filozofia/chrzescijanstwo",
            "subcategories": [
                {"id": "religion.christianity.catholicism", "names": {"pl": "Katolicyzm", "en": "Catholicism", "de": "Katholizismus"}, "path": "/religia_i_filozofia/chrzescijanstwo/katolicyzm"},
                {"id": "religion.christianity.orthodoxy", "names": {"pl": "Prawosławie", "en": "Orthodoxy", "de": "Orthodoxie"}, "path": "/religia_i_filozofia/chrzescijanstwo/prawoslawle"},
                {"id": "religion.christianity.protestantism", "names": {"pl": "Protestantyzm", "en": "Protestantism", "de": "Protestantismus"}, "path": "/religia_i_filozofia/chrzescijanstwo/protestantyzm"},
            ],
        },
        {
            "id": "religion.other_religions",
            "names": {"pl": "Inne religie", "en": "Other religions", "de": "Andere Religionen"},
            "path": "/religia_i_filozofia/inne_religie",
            "subcategories": [
                {"id": "religion.other_religions.islam", "names": {"pl": "Islam", "en": "Islam", "de": "Islam"}, "path": "/religia_i_filozofia/inne_religie/islam"},
                {"id": "religion.other_religions.judaism", "names": {"pl": "Judaizm", "en": "Judaism", "de": "Judentum"}, "path": "/religia_i_filozofia/inne_religie/judaizm"},
                {"id": "religion.other_religions.buddhism", "names": {"pl": "Buddyzm", "en": "Buddhism", "de": "Buddhismus"}, "path": "/religia_i_filozofia/inne_religie/buddyzm"},
                {"id": "religion.other_religions.hinduism", "names": {"pl": "Hinduizm", "en": "Hinduism", "de": "Hinduismus"}, "path": "/religia_i_filozofia/inne_religie/hinduizm"},
            ],
        },
        {
            "id": "religion.philosophy",
            "names": {"pl": "Filozofia", "en": "Philosophy", "de": "Philosophie"},
            "path": "/religia_i_filozofia/filozofia",
            "subcategories": [
                {"id": "religion.philosophy.ethics", "names": {"pl": "Etyka", "en": "Ethics", "de": "Ethik"}, "path": "/religia_i_filozofia/filozofia/etyka"},
                {"id": "religion.philosophy.logic", "names": {"pl": "Logika", "en": "Logic", "de": "Logik"}, "path": "/religia_i_filozofia/filozofia/logika"},
                {"id": "religion.philosophy.metaphysics", "names": {"pl": "Metafizyka", "en": "Metaphysics", "de": "Metaphysik"}, "path": "/religia_i_filozofia/filozofia/metafizyka"},
                {"id": "religion.philosophy.political", "names": {"pl": "Filozofia polityczna", "en": "Political philosophy", "de": "Politische Philosophie"}, "path": "/religia_i_filozofia/filozofia/filozofia_polityczna"},
                {"id": "religion.philosophy.history", "names": {"pl": "Historia filozofii", "en": "History of philosophy", "de": "Geschichte der Philosophie"}, "path": "/religia_i_filozofia/filozofia/historia_filozofii"},
            ],
        },
        {
            "id": "religion.spirituality",
            "names": {"pl": "Duchowość", "en": "Spirituality", "de": "Spiritualität"},
            "path": "/religia_i_filozofia/duchowosc",
            "subcategories": [
                {"id": "religion.spirituality.meditation", "names": {"pl": "Medytacja", "en": "Meditation", "de": "Meditation"}, "path": "/religia_i_filozofia/duchowosc/medytacja"},
                {"id": "religion.spirituality.prayer", "names": {"pl": "Modlitwa", "en": "Prayer", "de": "Gebet"}, "path": "/religia_i_filozofia/duchowosc/modlitwa"},
                {"id": "religion.spirituality.personal_growth", "names": {"pl": "Rozwój osobisty", "en": "Personal growth", "de": "Persönlichkeitsentwicklung"}, "path": "/religia_i_filozofia/duchowosc/rozwoj_osobisty"},
            ],
        },
    ],
}

# ============================================================================
# 13. ŚRODOWISKO I EKOLOGIA / ENVIRONMENT
# ============================================================================
ENVIRONMENT = {
    "id": "environment",
    "names": {"pl": "Środowisko i ekologia", "en": "Environment and ecology", "de": "Umwelt und Ökologie"},
    "path": "/srodowisko_i_ekologia",
    "path_hints": ["srodowisko", "ekologia", "environment", "ecology", "environmental",
                   "umwelt", "ökologie", "klimat", "climate", "recycling", "energia_odnawialna"],
    "keywords": {
        "pl": ["środowisko", "ekologia", "klimat", "przyroda", "zanieczyszczenie",
               "recykling", "energia odnawialna", "ochrona środowiska", "emisja",
               "fotowoltaika", "wiatrowa", "odpady", "segregacja", "biodiversity"],
        "en": ["environment", "ecology", "climate", "nature", "pollution",
               "recycling", "renewable energy", "environmental protection", "emissions",
               "solar", "wind energy", "waste", "segregation", "biodiversity"],
        "de": ["umwelt", "ökologie", "klima", "natur", "verschmutzung",
               "recycling", "erneuerbare energie", "umweltschutz", "emissionen",
               "photovoltaik", "windenergie", "abfall", "mülltrennung", "biodiversität"],
    },
    "subcategories": [
        {
            "id": "environment.nature_protection",
            "names": {"pl": "Ochrona przyrody", "en": "Nature protection", "de": "Naturschutz"},
            "path": "/srodowisko_i_ekologia/ochrona_przyrody",
            "subcategories": [
                {"id": "environment.nature_protection.species", "names": {"pl": "Gatunki", "en": "Species", "de": "Arten"}, "path": "/srodowisko_i_ekologia/ochrona_przyrody/gatunki"},
                {"id": "environment.nature_protection.national_parks", "names": {"pl": "Parki narodowe", "en": "National parks", "de": "Nationalparks"}, "path": "/srodowisko_i_ekologia/ochrona_przyrody/parki_narodowe"},
                {"id": "environment.nature_protection.reserves", "names": {"pl": "Rezerwaty", "en": "Reserves", "de": "Naturschutzgebiete"}, "path": "/srodowisko_i_ekologia/ochrona_przyrody/rezerwaty"},
            ],
        },
        {
            "id": "environment.pollution",
            "names": {"pl": "Zanieczyszczenia", "en": "Pollution", "de": "Umweltverschmutzung"},
            "path": "/srodowisko_i_ekologia/zanieczyszczenia",
            "subcategories": [
                {"id": "environment.pollution.air", "names": {"pl": "Powietrze", "en": "Air", "de": "Luft"}, "path": "/srodowisko_i_ekologia/zanieczyszczenia/powietrze"},
                {"id": "environment.pollution.water", "names": {"pl": "Woda", "en": "Water", "de": "Wasser"}, "path": "/srodowisko_i_ekologia/zanieczyszczenia/woda"},
                {"id": "environment.pollution.soil", "names": {"pl": "Gleba", "en": "Soil", "de": "Boden"}, "path": "/srodowisko_i_ekologia/zanieczyszczenia/gleba"},
                {"id": "environment.pollution.waste", "names": {"pl": "Odpady", "en": "Waste", "de": "Abfall"}, "path": "/srodowisko_i_ekologia/zanieczyszczenia/odpady"},
            ],
        },
        {
            "id": "environment.climate",
            "names": {"pl": "Klimat", "en": "Climate", "de": "Klima"},
            "path": "/srodowisko_i_ekologia/klimat",
            "subcategories": [
                {"id": "environment.climate.change", "names": {"pl": "Zmiany klimatu", "en": "Climate change", "de": "Klimawandel"}, "path": "/srodowisko_i_ekologia/klimat/zmiany_klimatu"},
                {"id": "environment.climate.adaptation", "names": {"pl": "Adaptacja", "en": "Adaptation", "de": "Anpassung"}, "path": "/srodowisko_i_ekologia/klimat/adaptacja"},
            ],
        },
        {
            "id": "environment.renewable_energy",
            "names": {"pl": "Energia odnawialna", "en": "Renewable energy", "de": "Erneuerbare Energie"},
            "path": "/srodowisko_i_ekologia/energia_odnawialna",
            "subcategories": [
                {"id": "environment.renewable_energy.solar", "names": {"pl": "Fotowoltaika", "en": "Solar", "de": "Photovoltaik"}, "path": "/srodowisko_i_ekologia/energia_odnawialna/fotowoltaika"},
                {"id": "environment.renewable_energy.wind", "names": {"pl": "Wiatrowa", "en": "Wind", "de": "Windenergie"}, "path": "/srodowisko_i_ekologia/energia_odnawialna/wiatrowa"},
                {"id": "environment.renewable_energy.hydro", "names": {"pl": "Wodna", "en": "Hydro", "de": "Wasserkraft"}, "path": "/srodowisko_i_ekologia/energia_odnawialna/wodna"},
                {"id": "environment.renewable_energy.geothermal", "names": {"pl": "Geotermalna", "en": "Geothermal", "de": "Geothermie"}, "path": "/srodowisko_i_ekologia/energia_odnawialna/geotermalna"},
                {"id": "environment.renewable_energy.biomass", "names": {"pl": "Biomasa", "en": "Biomass", "de": "Biomasse"}, "path": "/srodowisko_i_ekologia/energia_odnawialna/biomasa"},
            ],
        },
        {
            "id": "environment.recycling",
            "names": {"pl": "Recykling", "en": "Recycling", "de": "Recycling"},
            "path": "/srodowisko_i_ekologia/recykling",
            "subcategories": [
                {"id": "environment.recycling.segregation", "names": {"pl": "Segregacja", "en": "Segregation", "de": "Mülltrennung"}, "path": "/srodowisko_i_ekologia/recykling/segregacja"},
                {"id": "environment.recycling.composting", "names": {"pl": "Kompostowanie", "en": "Composting", "de": "Kompostierung"}, "path": "/srodowisko_i_ekologia/recykling/kompostowanie"},
                {"id": "environment.recycling.reuse", "names": {"pl": "Ponowne użycie", "en": "Reuse", "de": "Wiederverwendung"}, "path": "/srodowisko_i_ekologia/recykling/ponowne_uzycie"},
            ],
        },
    ],
}

# ============================================================================
# 14. INNE / OTHER
# ============================================================================
OTHER = {
    "id": "other",
    "names": {"pl": "Inne", "en": "Other", "de": "Sonstiges"},
    "path": "/inne",
    "path_hints": ["inne", "other", "sonstiges", "archiwum", "archive", "dokumenty_urzedowe",
                   "nieprzypisane", "unassigned"],
    "keywords": {
        "pl": ["dokument", "urząd", "wniosek", "pismo", "certyfikat", "akt",
               "archiwum", "historia", "pamiątka", "formularz"],
        "en": ["document", "office", "application", "letter", "certificate", "act",
               "archive", "history", "memento", "form"],
        "de": ["dokument", "amt", "antrag", "schreiben", "zertifikat", "akt",
               "archiv", "geschichte", "andenken", "formular"],
    },
    "subcategories": [
        {
            "id": "other.official_documents",
            "names": {"pl": "Dokumenty urzędowe", "en": "Official documents", "de": "Amtliche Dokumente"},
            "path": "/inne/dokumenty_urzedowe",
            "subcategories": [
                {"id": "other.official_documents.id", "names": {"pl": "Dowody i paszporty", "en": "IDs and passports", "de": "Ausweise und Pässe"}, "path": "/inne/dokumenty_urzedowe/dowody_i_paszporty"},
                {"id": "other.official_documents.civil", "names": {"pl": "Akty stanu cywilnego", "en": "Civil records", "de": "Personenstandsurkunden"}, "path": "/inne/dokumenty_urzedowe/akty_stanu_cywilnego"},
                {"id": "other.official_documents.certificates", "names": {"pl": "Certyfikaty", "en": "Certificates", "de": "Zertifikate"}, "path": "/inne/dokumenty_urzedowe/certyfikaty"},
                {"id": "other.official_documents.applications", "names": {"pl": "Pisma i wnioski", "en": "Letters and applications", "de": "Schreiben und Anträge"}, "path": "/inne/dokumenty_urzedowe/pisma_i_wnioski"},
            ],
        },
        {
            "id": "other.archive",
            "names": {"pl": "Archiwum", "en": "Archive", "de": "Archiv"},
            "path": "/inne/archiwum",
            "subcategories": [
                {"id": "other.archive.old_docs", "names": {"pl": "Stare dokumenty", "en": "Old documents", "de": "Alte Dokumente"}, "path": "/inne/archiwum/stare_dokumenty"},
                {"id": "other.archive.family_history", "names": {"pl": "Historia rodzinna", "en": "Family history", "de": "Familiengeschichte"}, "path": "/inne/archiwum/historia_rodzinna"},
                {"id": "other.archive.mementos", "names": {"pl": "Pamiątki", "en": "Mementos", "de": "Erinnerungsstücke"}, "path": "/inne/archiwum/pamiatki"},
            ],
        },
        {
            "id": "other.unassigned",
            "names": {"pl": "Nieprzypisane", "en": "Unassigned", "de": "Nicht zugewiesen"},
            "path": "/inne/nieprzypisane",
            "subcategories": [],
        },
    ],
}

# ============================================================================
# GŁÓWNY SŁOWNIK — WSZYSTKIE 14 KATEGORII
# ============================================================================

CATEGORIES: dict = {
    "medicine":     MEDICINE,
    "law":          LAW,
    "finance":      FINANCE,
    "technology":   TECHNOLOGY,
    "construction": CONSTRUCTION,
    "education":    EDUCATION,
    "agriculture":  AGRICULTURE,
    "society":      SOCIETY,
    "culture":      CULTURE,
    "sport":        SPORT,
    "family":       FAMILY,
    "religion":     RELIGION,
    "environment":  ENVIRONMENT,
    "other":        OTHER,
}


# ============================================================================
# FUNKCJE POMOCNICZE
# ============================================================================

def get_category_ids() -> list[str]:
    """Zwraca listę wszystkich ID kategorii (bez 'other')."""
    return [k for k in CATEGORIES if k != "other"]


def get_category_name(category_id: str, lang: str = "pl") -> str:
    """Zwraca zlokalizowaną nazwę kategorii."""
    cat = CATEGORIES.get(category_id)
    if not cat:
        return category_id
    return cat["names"].get(lang, cat["names"]["pl"])


def get_all_keywords(lang: str = "pl") -> dict[str, list[str]]:
    """Zwraca słownik {category_id: [keywords]} dla danego języka."""
    return {
        cat_id: cat["keywords"].get(lang, cat["keywords"]["pl"])
        for cat_id, cat in CATEGORIES.items()
        if cat_id != "other"
    }


def get_path_hints() -> dict[str, list[str]]:
    """Zwraca słownik {category_id: [path_hints]} dla klasyfikacji po ścieżce."""
    return {
        cat_id: cat.get("path_hints", [])
        for cat_id, cat in CATEGORIES.items()
        if cat_id != "other"
    }
