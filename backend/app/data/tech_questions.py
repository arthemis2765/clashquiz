# Questions "Technologie" : informatique, internet, entreprises tech, programmation,
# IA, cybersécurité, histoire de l'informatique.
# Format identique à sport_questions.py : (prompt_label, answer, hint_type, hint_code, difficulty)
#
# Les réponses sont comparées après normalisation (casse, accents, espaces ignorés) :
# elles sont donc courtes et sans article, avec une seule forme canonique.
# 80 questions : 16 par niveau de difficulté (1 à 5), dont une vingtaine sur l'IA.

TECH_QUESTIONS = [
    # --- Difficulté 1 ---
    ("Quel appareil, avec deux boutons et souvent une molette, sert à déplacer le curseur sur un ordinateur ?", "Souris", "text", None, 1),
    ("Quelle entreprise a créé l'iPhone ?", "Apple", "text", None, 1),
    ("Quel moteur de recherche est le plus utilisé au monde ?", "Google", "text", None, 1),
    ("Quel réseau social avait un oiseau bleu pour logo avant de devenir X ?", "Twitter", "text", None, 1),
    ("Combien de bits y a-t-il dans un octet ?", "8", "text", None, 1),
    ("Comment s'appelle l'assistant vocal d'Apple ?", "Siri", "text", None, 1),
    ("Quelle entreprise a créé le système d'exploitation Windows ?", "Microsoft", "text", None, 1),
    ("Quel système d'exploitation mobile de Google équipe la majorité des smartphones dans le monde ?", "Android", "text", None, 1),
    ("Quelle application de messagerie, propriété de Meta, a un logo vert avec un combiné téléphonique ?", "WhatsApp", "text", None, 1),
    ("Quelle plateforme de partage de vidéos a un logo rouge avec un triangle blanc ?", "YouTube", "text", None, 1),
    ("Quel composant est considéré comme le « cerveau » de l'ordinateur ?", "Processeur", "text", None, 1),
    ("Comment s'appelle la boutique d'applications d'Apple ?", "App Store", "text", None, 1),

    ("Que signifie le sigle IA ?", "Intelligence artificielle", "text", None, 1),
    ("Comment s'appelle l'assistant IA créé par Anthropic ?", "Claude", "text", None, 1),
    ("Quel mot anglais désigne un robot qui discute avec les humains par messages, comme ChatGPT ?", "Chatbot", "text", None, 1),
    ("Quelle entreprise japonaise a créé la console de jeux Switch ?", "Nintendo", "text", None, 1),

    # --- Difficulté 2 ---
    ("Quel langage de balisage sert à structurer les pages web ?", "HTML", "text", None, 2),
    ("Quel cofondateur d'Apple, disparu en 2011, a présenté le premier iPhone ?", "Steve Jobs", "text", None, 2),
    ("Quel système d'exploitation libre a pour mascotte un manchot ?", "Linux", "text", None, 2),
    ("Que signifie le sigle USB ? (en anglais)", "Universal Serial Bus", "text", None, 2),
    ("Qui a fondé Microsoft avec Paul Allen en 1975 ?", "Bill Gates", "text", None, 2),
    ("Comment s'appelle le navigateur web de la fondation Mozilla ?", "Firefox", "text", None, 2),
    ("Quel réseau social a été lancé en 2004 par Mark Zuckerberg ?", "Facebook", "text", None, 2),
    ("Quelle unité de stockage suit le mégaoctet, avant le téraoctet ?", "Gigaoctet", "text", None, 2),
    ("Comment s'appelle le moteur de recherche de Microsoft ?", "Bing", "text", None, 2),
    ("Quelle entreprise vend les smartphones de la gamme Galaxy ?", "Samsung", "text", None, 2),
    ("Dans quel pays est née la marque de téléphones Nokia ?", "Finlande", "flag", "fi", 2),
    ("Quelle application de vidéos courtes, lancée par ByteDance, est célèbre pour ses danses et ses défis ?", "TikTok", "text", None, 2),

    ("Quelle entreprise a créé ChatGPT ?", "OpenAI", "text", None, 2),
    ("Comment s'appelle l'assistant IA de Google, successeur de Bard depuis 2024 ?", "Gemini", "text", None, 2),
    ("Comment appelle-t-on, en anglais, le texte d'instructions qu'on donne à une IA générative ?", "Prompt", "text", None, 2),
    ("Quel réseau social professionnel appartient à Microsoft depuis 2016 ?", "LinkedIn", "text", None, 2),

    # --- Difficulté 3 ---
    ("Qui a inventé le World Wide Web en 1989 au CERN ?", "Tim Berners-Lee", "text", None, 3),
    ("Quel langage de programmation, créé par Guido van Rossum, doit son nom à une troupe d'humoristes britanniques ?", "Python", "text", None, 3),
    ("En quelle année le premier iPhone est-il sorti ?", "2007", "text", None, 3),
    ("Comment s'appelle la société mère de Google depuis 2015 ?", "Alphabet", "text", None, 3),
    ("Dans quel pays se trouve le siège de Samsung ?", "Corée du Sud", "flag", "kr", 3),
    ("Quel protocole sécurisé, avec un cadenas dans le navigateur, remplace le simple HTTP ?", "HTTPS", "text", None, 3),
    ("Quel langage sert à mettre en forme les pages web (couleurs, polices, mise en page) ?", "CSS", "text", None, 3),
    ("Quelle monnaie numérique a été créée en 2009 par le mystérieux Satoshi Nakamoto ?", "Bitcoin", "text", None, 3),
    ("Comment s'appelle le robot conversationnel d'OpenAI lancé en novembre 2022 ?", "ChatGPT", "text", None, 3),
    ("Dans quel pays sont nées les entreprises Sony et Nintendo ?", "Japon", "flag", "jp", 3),
    ("Quelle plateforme d'hébergement de code, rachetée par Microsoft en 2018, est très utilisée par les développeurs ?", "GitHub", "text", None, 3),
    ("Combien d'octets compte un kilooctet dans la convention binaire historique ?", "1024", "text", None, 3),

    ("Comment s'appelle l'IA d'OpenAI qui génère des images à partir d'un texte, dont le nom mêle un peintre surréaliste et un robot de Pixar ?", "DALL-E", "text", None, 3),
    ("Quel terme anglais désigne la branche de l'IA où les machines apprennent à partir de données ?", "Machine learning", "text", None, 3),
    ("Quel terme désigne un faux contenu vidéo ou audio ultra-réaliste, généré par IA, qui imite une vraie personne ?", "Deepfake", "text", None, 3),
    ("Quel jeu vidéo en blocs, racheté par Microsoft en 2014, permet de tout construire ?", "Minecraft", "text", None, 3),

    # --- Difficulté 4 ---
    ("Quelle mathématicienne britannique est considérée comme la première programmeuse de l'histoire grâce à ses notes sur la machine de Babbage ?", "Ada Lovelace", "text", None, 4),
    ("Comment s'appelle l'ancêtre d'Internet, réseau créé à la fin des années 1960 aux États-Unis ?", "ARPANET", "text", None, 4),
    ("Quelle unité mesure la fréquence d'un processeur (en GHz) ?", "Hertz", "text", None, 4),
    ("Quel langage a été créé en 1995 par Brendan Eich en une dizaine de jours pour le navigateur Netscape ?", "JavaScript", "text", None, 4),
    ("Quel système de gestion de versions a été créé par Linus Torvalds en 2005 ?", "Git", "text", None, 4),
    ("Quel protocole attribue automatiquement une adresse IP aux appareils d'un réseau ?", "DHCP", "text", None, 4),
    ("Quelle entreprise conçoit les processeurs de la gamme Ryzen ?", "AMD", "text", None, 4),
    ("Quel langage est utilisé pour interroger les bases de données relationnelles ?", "SQL", "text", None, 4),
    ("En quelle année Google a-t-il été fondé ?", "1998", "text", None, 4),
    ("Quel terme anglais désigne une fausse communication qui cherche à voler vos identifiants en se faisant passer pour un organisme de confiance ?", "Phishing", "text", None, 4),
    ("Dans quel pays a été conçue l'architecture de processeurs ARM, présente dans la plupart des smartphones ?", "Royaume-Uni", "flag", "gb", 4),
    ("Quelle cryptomonnaie, proposée par Vitalik Buterin, est la plus connue après le Bitcoin ?", "Ethereum", "text", None, 4),

    ("Comment s'appelle l'IA de DeepMind qui a battu le champion de go Lee Sedol en 2016 ?", "AlphaGo", "text", None, 4),
    ("Quelle architecture de réseau de neurones, introduite par Google en 2017, est à la base des grands modèles de langage ?", "Transformer", "text", None, 4),
    ("Que signifie le sigle LLM ? (en anglais)", "Large Language Model", "text", None, 4),
    ("Quelle technologie sans fil à courte portée porte le nom d'un roi viking ?", "Bluetooth", "text", None, 4),

    # --- Difficulté 5 ---
    ("Quel mathématicien britannique a proposé en 1950 un test pour savoir si une machine peut penser ?", "Alan Turing", "text", None, 5),
    ("Comment s'appelle l'ordinateur d'IBM qui a battu le champion d'échecs Garry Kasparov en 1997 ?", "Deep Blue", "text", None, 5),
    ("Quel est le numéro du premier microprocesseur commercial d'Intel, sorti en 1971 ? (Intel ...)", "4004", "text", None, 5),
    ("Quel modèle de réseau est décomposé en sept couches, de la couche physique à la couche application ?", "OSI", "text", None, 5),
    ("Quel ingénieur et mathématicien américain a fondé la théorie de l'information en 1948 ?", "Claude Shannon", "text", None, 5),
    ("Quel langage de programmation, créé par Dennis Ritchie aux Bell Labs vers 1972, porte le nom d'une seule lettre ?", "C", "text", None, 5),
    ("Quel projet, lancé par Richard Stallman en 1983, visait à créer un système d'exploitation entièrement libre ?", "GNU", "text", None, 5),
    ("Quel système d'exploitation, né aux Bell Labs en 1969, a inspiré Linux et macOS ?", "Unix", "text", None, 5),
    ("Quel algorithme de chiffrement à clé publique, inventé en 1977, porte les initiales de ses trois créateurs ?", "RSA", "text", None, 5),
    ("Combien de bits comporte une adresse IPv6 ?", "128", "text", None, 5),
    ("Quelle machine de chiffrement allemande de la Seconde Guerre mondiale a été percée à Bletchley Park ?", "Enigma", "text", None, 5),
    ("Quelle plateforme de conteneurs, lancée en 2013, a popularisé le déploiement d'applications « dans une boîte » ?", "Docker", "text", None, 5),
    ("Quel chercheur américain a organisé la conférence de Dartmouth en 1956, où le terme « intelligence artificielle » a été utilisé ?", "John McCarthy", "text", None, 5),
    ("Comment s'appelle le programme de DeepMind qui a prédit la structure de millions de protéines ?", "AlphaFold", "text", None, 5),
    ("Quel chercheur français, prix Turing 2018 avec Geoffrey Hinton et Yoshua Bengio, est pionnier des réseaux de neurones convolutifs ?", "Yann LeCun", "text", None, 5),
    ("Quel ordinateur d'IBM a remporté le jeu télévisé Jeopardy! en 2011 ?", "Watson", "text", None, 5),
]
