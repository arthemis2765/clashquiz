# Questions "Culture générale" : sciences, histoire, arts, société, géographie
# générale (hors pur drapeau, déjà couvert par la catégorie Géographie).
# Format identique à sport_questions.py : (prompt_label, answer, hint_type, hint_code, difficulty)

CULTURE_QUESTIONS = [
    # --- Difficulté 1 ---
    ("Combien de continents compte-t-on sur Terre ?", "7", "text", None, 1),
    ("Quelle est la planète la plus proche du Soleil ?", "Mercure", "text", None, 1),
    ("Combien de couleurs composent l'arc-en-ciel ?", "7", "text", None, 1),
    ("Quel est l'océan le plus grand du monde ?", "Océan Pacifique", "text", None, 1),
    ("Quelle langue est parlée au Gabon comme langue officielle ?", "Français", "text", None, 1),
    ("Combien de jours compte une année bissextile ?", "366", "text", None, 1),
    ("Quel est l'organe du corps humain qui pompe le sang ?", "Le cœur", "text", None, 1),
    ("Quel pays est réputé pour la tour Eiffel ?", "France", "flag", "fr", 1),
    ("Quel est le plus long fleuve d'Afrique ?", "Le Nil", "text", None, 1),
    ("Combien de continents l'Afrique compte-t-elle... pardon, combien de pays compte l'Afrique environ ?", "54", "text", None, 1),

    # --- Difficulté 2 ---
    ("Quelle est la capitale du Gabon ?", "Libreville", "text", None, 2),
    ("Quel est le plus grand désert chaud du monde ?", "Le Sahara", "text", None, 2),
    ("Quel savant est célèbre pour la théorie de la relativité ?", "Albert Einstein", "text", None, 2),
    ("Quelle est la monnaie utilisée au Gabon ?", "Franc CFA", "text", None, 2),
    ("Quel pays est le plus peuplé du monde (au dernier recensement connu) ?", "Inde", "flag", "in", 2),
    ("En quelle année l'homme a-t-il marché sur la Lune pour la première fois ?", "1969", "text", None, 2),
    ("Quel est le plus grand pays d'Afrique par la superficie ?", "Algérie", "flag", "dz", 2),
    ("Quel peintre est célèbre pour le tableau 'La Joconde' ?", "Léonard de Vinci", "text", None, 2),
    ("Quelle est la plus haute montagne du monde ?", "Everest", "text", None, 2),
    ("Quel pays africain est le premier producteur mondial de cacao ?", "Côte d'Ivoire", "flag", "ci", 2),
    ("Quelle est la capitale de l'Égypte ?", "Le Caire", "text", None, 2),
    ("Combien d'os compte le corps humain adulte, approximativement ?", "206", "text", None, 2),

    # --- Difficulté 3 ---
    ("En quelle année le Gabon a-t-il obtenu son indépendance ?", "1960", "text", None, 3),
    ("Quel est le nom du premier président de la République gabonaise ?", "Léon M'ba", "text", None, 3),
    ("Quelle est la plus grande forêt tropicale du monde ?", "La forêt amazonienne", "text", None, 3),
    ("Quel scientifique a formulé les lois de la gravitation universelle ?", "Isaac Newton", "text", None, 3),
    ("Quel pays a inventé l'imprimerie moderne à caractères mobiles, au XVe siècle ?", "Allemagne", "flag", "de", 3),
    ("Quelle est la langue la plus parlée au monde en nombre de locuteurs natifs ?", "Le mandarin", "text", None, 3),
    ("Quel est le nom du parc national gabonais réputé pour ses éléphants de forêt, sur la côte atlantique ?", "Parc national de Loango", "text", None, 3),
    ("Quel philosophe grec antique fut le maître d'Alexandre le Grand ?", "Aristote", "text", None, 3),
    ("Quelle organisation internationale a son siège à Genève et s'occupe de la santé mondiale ?", "Organisation mondiale de la santé (OMS)", "text", None, 3),
    ("Quel est le plus petit pays du monde par la superficie ?", "Vatican", "text", None, 3),
    ("Quel est le nom du courant artistique auquel appartient Pablo Picasso, qu'il a co-fondé ?", "Le cubisme", "text", None, 3),

    # --- Difficulté 4 ---
    ("Quel est le nom du fleuve principal qui traverse le Gabon ?", "L'Ogooué", "text", None, 4),
    ("En quelle année l'Organisation des Nations unies (ONU) a-t-elle été fondée ?", "1945", "text", None, 4),
    ("Quel est le nom de la théorie qui explique l'origine de l'univers par une expansion initiale ?", "Le Big Bang", "text", None, 4),
    ("Quel écrivain gabonais est notamment connu pour le roman 'Elonga' ?", "Laurent Owondo", "text", None, 4),
    ("Quelle est la capitale administrative du Nigeria (différente de sa plus grande ville) ?", "Abuja", "text", None, 4),
    ("Quel physicien a proposé la théorie de l'évolution des espèces par sélection naturelle ?", "Charles Darwin", "text", None, 4),
    ("Quel est le nom de l'écosystème unique et protégé formé par les tourbières de la Cuvette centrale, à cheval entre le Gabon, le Congo et la RDC ?", "La cuvette centrale congolaise", "text", None, 4),
    ("Quelle est l'unité de mesure de l'intensité d'un tremblement de terre ?", "L'échelle de Richter (magnitude)", "text", None, 4),
    ("Quel roi de France est resté au pouvoir le plus longtemps de l'histoire, sous le nom de 'Roi Soleil' ?", "Louis XIV", "text", None, 4),
    ("Quel pays a été le premier à envoyer un satellite artificiel en orbite (Spoutnik, 1957) ?", "Russie", "flag", "ru", 4),

    # --- Difficulté 5 ---
    ("Quel est le nom du traité qui a établi les frontières coloniales de l'Afrique en 1884-1885 ?", "La conférence de Berlin", "text", None, 5),
    ("Quel est le nom scientifique de la molécule support de l'information génétique ?", "ADN (acide désoxyribonucléique)", "text", None, 5),
    ("Quel explorateur franco-italien est à l'origine de la fondation de Libreville et Brazzaville, au XIXe siècle ?", "Pierre Savorgnan de Brazza", "text", None, 5),
    ("Quel est le nom du prix récompensant chaque année les avancées majeures en sciences, littérature et paix, créé par un industriel suédois ?", "Le prix Nobel", "text", None, 5),
    ("Quelle est la particule subatomique découverte en 2012 au CERN, surnommée 'particule de Dieu' ?", "Le boson de Higgs", "text", None, 5),
    ("Quel est le nom de l'ethnie majoritaire au Gabon par le nombre de locuteurs ?", "Les Fang", "text", None, 5),
    ("En quelle année a eu lieu la conférence de La Baule, marquant un tournant démocratique pour l'Afrique francophone ?", "1990", "text", None, 5),
    ("Quel est le nom du plus grand gisement de manganèse du Gabon, exploité près de Moanda ?", "Moanda (gisement de Bangombé/Okouma)", "text", None, 5),
    ("Quel astronome polonais a proposé le modèle héliocentrique du système solaire au XVIe siècle ?", "Nicolas Copernic", "text", None, 5),
    ("Quel est le nom du mouvement littéraire porté notamment par Aimé Césaire et Léopold Sédar Senghor, valorisant l'identité culturelle africaine ?", "La négritude", "text", None, 5),
]
