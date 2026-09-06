# Questions "Sport" (football uniquement) : large couverture africaine
# (Sénégal, Côte d'Ivoire, Maroc, Égypte, Cameroun, Nigeria, Ghana, Algérie,
# Tunisie, Afrique du Sud, Mali, RDC, Gabon...) + scène internationale.
#
# Chaque entrée : (prompt_label, answer, hint_type, hint_code_or_none, difficulty)
#   - hint_type="flag"  -> hint_code est un code pays ISO (utilisé avec flag_url), la
#     réponse attendue est le nom de ce pays.
#   - hint_type="text"  -> hint_code est None, la question complète est dans prompt_label,
#     la réponse peut être un joueur, un club, un nombre, une année...
#
# Pas de logos de clubs ni de photos de joueurs réels (droits de marque / image) :
# uniquement du texte et des drapeaux de pays, cohérent avec la catégorie Géographie.

SPORT_QUESTIONS = [
    # --- Difficulté 1 : évident pour tout amateur de foot ---
    ("Quel pays a remporté la Coupe du monde de football 2022 ?", "Argentine", "flag", "ar", 1),
    ("Quel pays a remporté la Coupe du monde de football 2018 ?", "France", "flag", "fr", 1),
    ("Combien de joueurs une équipe de football aligne-t-elle sur le terrain (gardien inclus) ?", "11", "text", None, 1),
    ("Combien de temps dure un match de football en temps réglementaire (hors prolongations) ?", "90 minutes", "text", None, 1),
    ("Quel pays organise la Coupe d'Afrique des Nations (CAN) 2025 ?", "Maroc", "flag", "ma", 1),
    ("Quelle couleur de carton signifie une exclusion définitive du joueur ?", "Rouge", "text", None, 1),
    ("Combien de temps dure une mi-temps de football ?", "45 minutes", "text", None, 1),
    ("Quel pays a remporté la CAN 2021 (jouée en 2022) ?", "Sénégal", "flag", "sn", 1),
    ("Quel est le nombre de joueurs remplaçables autorisés en Ligue 1 depuis 2022 ?", "5", "text", None, 1),
    ("De quel pays est originaire l'attaquant Sadio Mané ?", "Sénégal", "flag", "sn", 1),
    ("De quel pays est originaire l'attaquant Mohamed Salah ?", "Égypte", "flag", "eg", 1),

    # --- Difficulté 2 : bon niveau général ---
    ("Combien de fois l'Égypte a-t-elle remporté la CAN, un record continental ?", "7", "text", None, 2),
    ("Quel pays africain a été le premier à atteindre les quarts de finale d'une Coupe du monde (1990) ?", "Cameroun", "flag", "cm", 2),
    ("Quel pays a remporté la première Coupe du monde de football, en 1930 ?", "Uruguay", "flag", "uy", 2),
    ("Quel pays a accueilli la Coupe du monde 2010, la première organisée en Afrique ?", "Afrique du Sud", "flag", "za", 2),
    ("Quel pays a remporté la Coupe du monde de football 2010 ?", "Espagne", "flag", "es", 2),
    ("Combien de fois le Brésil a-t-il remporté la Coupe du monde, un record mondial ?", "5", "text", None, 2),
    ("Quel pays a remporté la CAN 2019, organisée en Égypte ?", "Algérie", "flag", "dz", 2),
    ("Combien d'équipes participent à la phase finale de la Coupe du monde depuis 1998 ?", "32", "text", None, 2),
    ("Quel pays a remporté la Coupe du monde de football 2014 ?", "Allemagne", "flag", "de", 2),
    ("De quel pays est originaire le Ballon d'or 2022, Karim Benzema ?", "France", "flag", "fr", 2),
    ("De quel pays est originaire l'attaquant Victor Osimhen ?", "Nigeria", "flag", "ng", 2),
    ("Combien de fois le Ghana a-t-il remporté la Coupe d'Afrique des Nations ?", "4", "text", None, 2),
    ("De quel pays est originaire le capitaine Riyad Mahrez ?", "Algérie", "flag", "dz", 2),

    # --- Difficulté 3 : demande un peu de suivi régulier du foot ---
    ("Quel pays africain a atteint les demi-finales de la Coupe du monde 2022, une première pour le continent ?", "Maroc", "flag", "ma", 3),
    ("Quel pays a remporté le plus de fois la Coupe d'Afrique des Nations avant 2020, l'Égypte mise à part ?", "Cameroun", "flag", "cm", 3),
    ("Quel pays a remporté la Coupe du monde féminine de football 2023 ?", "Espagne", "flag", "es", 3),
    ("Quel pays organisera la Coupe du monde de football masculin 2026 ?", "États-Unis", "flag", "us", 3),
    ("Quelle compétition inter-clubs annuelle oppose les meilleurs clubs africains, équivalent de la Ligue des champions ?", "Ligue des champions de la CAF", "text", None, 3),
    ("Quel pays a remporté la CAN 2017, disputée au Gabon ?", "Cameroun", "flag", "cm", 3),
    ("Quel pays a remporté la CAN 2015, disputée en Guinée équatoriale ?", "Côte d'Ivoire", "flag", "ci", 3),
    ("De quel pays est originaire le milieu de terrain Yaya Touré ?", "Côte d'Ivoire", "flag", "ci", 3),
    ("De quel pays est originaire l'ancien gardien Vincent Enyeama ?", "Nigeria", "flag", "ng", 3),
    ("Quel pays a organisé et remporté la CAN 2023 (jouée en 2024) ?", "Côte d'Ivoire", "flag", "ci", 3),
    ("Combien de joueurs composent une équipe de football à 7 (format réduit) ?", "7", "text", None, 3),
    ("De quel pays est originaire l'attaquant Achraf Hakimi ?", "Maroc", "flag", "ma", 3),

    # --- Difficulté 4 : niveau connaisseur ---
    ("Quel pays a remporté la toute première édition de la CAN, en 1957 ?", "Égypte", "flag", "eg", 4),
    ("Quel pays d'Afrique de l'Ouest a été sacré champion d'Afrique en 2015 sous le surnom des 'Éléphants' ?", "Côte d'Ivoire", "flag", "ci", 4),
    ("Quel est le nom de la fédération qui organise le football sur le continent africain ?", "Confédération africaine de football (CAF)", "text", None, 4),
    ("Combien de journées compte un championnat de Ligue 1 française à 18 équipes ?", "34", "text", None, 4),
    ("Quel pays a remporté la Coupe du monde de football 1998, en tant que pays hôte ?", "France", "flag", "fr", 4),
    ("Quel gardien de but camerounais est régulièrement cité parmi les meilleurs gardiens africains de l'histoire ?", "Thomas N'Kono", "text", None, 4),
    ("De quel pays est originaire l'ancien Ballon d'or africain George Weah, plus tard président de son pays ?", "Liberia", "flag", "lr", 4),
    ("Quel pays a remporté la CAN 1998, disputée au Burkina Faso ?", "Égypte", "flag", "eg", 4),
    ("Combien de fois le Sénégal a-t-il disputé une finale de CAN avant son titre de 2021 ?", "1", "text", None, 4),
    ("Quel est le surnom de l'équipe nationale de football du Gabon ?", "Les Panthères", "text", None, 4),
    ("Quel pays a remporté la CAN 2004, disputée en Tunisie ?", "Tunisie", "flag", "tn", 4),
    ("De quel pays est originaire l'attaquant historique Samuel Eto'o ?", "Cameroun", "flag", "cm", 4),

    # --- Difficulté 5 : pointu ---
    ("Quel est le nom du sélectionneur qui a mené le Sénégal à son premier titre continental en 2021 ?", "Aliou Cissé", "text", None, 5),
    ("Quelle est la première Coupe d'Afrique des Nations à avoir utilisé l'assistance vidéo à l'arbitrage (VAR) ?", "CAN 2019", "text", None, 5),
    ("Quel pays a remporté la toute première Coupe d'Afrique des Nations féminine, en 1991 ?", "Nigeria", "flag", "ng", 5),
    ("Combien de titres continentaux la sélection féminine du Nigeria compte-t-elle en Coupe d'Afrique des Nations féminine (record) ?", "11", "text", None, 5),
    ("En quelle année la Confédération africaine de football (CAF) a-t-elle été fondée ?", "1957", "text", None, 5),
    ("Quel pays a remporté la médaille d'or olympique de football aux Jeux de 1996 à Atlanta, une première pour l'Afrique ?", "Nigeria", "flag", "ng", 5),
    ("Quel est le nom du prix individuel annuel décerné au meilleur footballeur du continent africain par la CAF ?", "CAF Footballer of the Year (Joueur africain de l'année)", "text", None, 5),
    ("De quel pays est originaire le gardien Édouard Mendy, sacré champion d'Afrique en 2021 ?", "Sénégal", "flag", "sn", 5),
    ("Quel entraîneur gabonais historique, ancien international français, a dirigé les Panthères du Gabon dans les années 2010 ?", "Alain Giresse", "text", None, 5),
]
