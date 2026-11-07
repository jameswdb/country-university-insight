import re
# -*- coding: utf-8 -*-
"""Shared taxonomies: research-domain attribution and tier labels.

Order matters: the first rule that matches a *word-start* anywhere in the topic
string wins, so specific prefixes (Particle, Quantum, Materials) come before
generic ones (Art, Data, Cell).

Technion / HUJI / BGU / BIU / Haifa / Reichman / Ariel / HIT all lack a usable
public department field in OpenAlex, so affiliation is approximated from the
author's top OpenAlex topics. Same table for every university keeps the ten
reports comparable.
"""

# ordered: more specific prefixes first
TOPIC_RULES = [
    # physics
    ('Particle', 'physics'), ('Quantum', 'physics'), ('Astrophysics', 'physics'),
    ('Condensed', 'physics'), ('Optics', 'physics'), ('Stellar', 'physics'),
    ('Nuclear', 'physics'), ('Plasma', 'physics'), ('Dark Matter', 'physics'),
    # chemistry
    ('Chemistry', 'chemistry'), ('Catalysis', 'chemistry'), ('Electrochem', 'chemistry'),
    ('Polymer', 'chemistry'), ('Organic', 'chemistry'), ('Spectroscopy', 'chemistry'),
    ('Chromatograph', 'chemistry'), ('Crystallograph', 'chemistry'),
    # materials
    ('Materials', 'materials'), ('Metallurg', 'materials'), ('Nanomaterial', 'materials'),
    ('Semiconductor', 'materials'), ('Ceramic', 'materials'), ('Thin Film', 'materials'),
    ('Graphene', 'materials'), ('2D Materials', 'materials'),
    # engineering
    ('Electrical', 'engineering'), ('Signal', 'engineering'), ('Communication', 'engineering'),
    ('Control', 'engineering'), ('Mechanical', 'engineering'), ('Fluid', 'engineering'),
    ('Heat', 'engineering'), ('Robotics', 'engineering'), ('Aerospace', 'engineering'),
    ('Aerodynamic', 'engineering'), ('Civil', 'engineering'), ('Structural', 'engineering'),
    ('Transportation', 'engineering'), ('Geotechnical', 'engineering'), ('Soil', 'engineering'),
    ('Combustion', 'engineering'), ('Pulsed Power', 'engineering'), ('Antenna', 'engineering'),
    ('Radar', 'engineering'), ('Wireless', 'engineering'), ('Photovoltaic', 'engineering'),
    ('Chemical Engineering', 'engineering'), ('Biotechnology', 'engineering'),
    ('Biomedical', 'engineering'), ('Tissue Engineering', 'engineering'),
    # computing
    ('Computer', 'computer science'), ('Machine Learning', 'computer science'),
    ('Neural', 'computer science'), ('Algorithm', 'computer science'),
    ('Cryptograph', 'computer science'), ('Computer Vision', 'computer science'),
    ('Natural Language', 'computer science'), ('Software', 'computer science'),
    ('Information', 'computer science'), ('Data', 'computer science'),
    ('Speech', 'computer science'), ('Vision', 'computer science'),
    ('Computing', 'computer science'), ('Network', 'computer science'),
    ('Programming', 'computer science'), ('Optimization', 'computer science'),
    # mathematics
    ('Mathematics', 'mathematics'), ('Statistics', 'mathematics'),
    ('Probability', 'mathematics'), ('Topology', 'mathematics'),
    ('Algebra', 'mathematics'), ('Numerical', 'mathematics'), ('Stochastic', 'mathematics'),
    ('Variational', 'mathematics'), ('Combinatorics', 'mathematics'),
    # life sciences
    ('Biolog', 'life sciences'), ('Genetic', 'life sciences'), ('Molecular', 'life sciences'),
    ('Cell', 'life sciences'), ('Ecology', 'life sciences'), ('Evolution', 'life sciences'),
    ('Plant', 'life sciences'), ('Immunolog', 'life sciences'), ('Protein', 'life sciences'),
    ('Microbiolog', 'life sciences'), ('Genomics', 'life sciences'), ('Bioinformatic', 'life sciences'),
    ('Neuroscience', 'neuroscience'), ('Brain', 'neuroscience'), ('Neural Circuit', 'neuroscience'),
    # medicine
    ('Medicine', 'medicine'), ('Clinical', 'medicine'), ('Cancer', 'medicine'),
    ('Cardiolog', 'medicine'), ('Cardiac', 'medicine'), ('Cardiovascular', 'medicine'),
    ('Coronary', 'medicine'), ('Vascular', 'medicine'), ('Surgery', 'medicine'),
    ('Epidemiolog', 'medicine'), ('Health', 'medicine'), ('Nursing', 'medicine'),
    ('Diabetes', 'medicine'), ('Inflammatory', 'medicine'), ('Retinal', 'medicine'),
    ('Glaucoma', 'medicine'), ('Hepatitis', 'medicine'), ('Cystic Fibrosis', 'medicine'),
    ('Schizophrenia', 'medicine'), ('Parkinson', 'medicine'), ('Alzheimer', 'medicine'),
    ('COPD', 'medicine'), ('Pulmonary', 'medicine'), ('Obesity', 'medicine'),
    ('Imaging', 'medicine'), ('Ultrasound', 'medicine'), ('Radiolog', 'medicine'),
    ('Blood', 'medicine'), ('Thrombosis', 'medicine'), ('Pregnancy', 'medicine'),
    ('Fertility', 'medicine'), ('Psychiatr', 'medicine'),
    # environment
    ('Environment', 'environment'), ('Climate', 'environment'), ('Energy', 'environment'),
    ('Sustainability', 'environment'), ('Water', 'environment'), ('Air Pollution', 'environment'),
    ('Solar', 'environment'), ('Battery', 'environment'), ('Earth', 'environment'),
    # social sciences / management / humanities
    ('Economic', 'social sciences'), ('Labor', 'social sciences'), ('Political', 'social sciences'),
    ('Sociolog', 'social sciences'), ('Psychology', 'social sciences'),
    ('Social', 'social sciences'), ('Education', 'social sciences'), ('Learning', 'social sciences'),
    ('Management', 'management'), ('Marketing', 'management'), ('Finance', 'management'),
    ('Operations', 'management'), ('Decision', 'management'), ('Accounting', 'management'),
    ('Entrepreneur', 'management'), ('Supply Chain', 'management'),
    ('Architecture', 'architecture'), ('Urban', 'architecture'), ('Housing', 'architecture'),
    ('Building', 'architecture'), ('Construction', 'architecture'), ('Landscape', 'architecture'),
    ('History', 'humanities'), ('Philosophy', 'humanities'), ('Art', 'humanities'),
    ('Literature', 'humanities'), ('Religion', 'humanities'), ('Jewish', 'humanities'),
    ('Language', 'humanities'), ('Archaeolog', 'humanities'), ('Bible', 'humanities'),
    ('Law', 'law'), ('Legal', 'law'), ('Criminol', 'law'),
]

DOMAIN_EN = {
    'physics': 'Physics & Astronomy', 'chemistry': 'Chemistry', 'materials': 'Materials Science',
    'engineering': 'Engineering', 'computer science': 'Computer Science',
    'mathematics': 'Mathematics', 'life sciences': 'Life Sciences',
    'neuroscience': 'Neuroscience', 'medicine': 'Medicine',
    'environment': 'Environment & Energy', 'social sciences': 'Social Sciences',
    'management': 'Management', 'architecture': 'Architecture & Planning',
    'humanities': 'Humanities', 'law': 'Law', 'other': 'Other',
}
DOMAIN_ZH = {
    'physics': '物理与天文', 'chemistry': '化学', 'materials': '材料科学',
    'engineering': '工程', 'computer science': '计算机科学', 'mathematics': '数学',
    'life sciences': '生命科学', 'neuroscience': '神经科学', 'medicine': '医学',
    'environment': '环境与能源', 'social sciences': '社会科学', 'management': '管理学',
    'architecture': '建筑与规划', 'humanities': '人文', 'law': '法学', 'other': '其他',
}

TIER_ZH = {
    'A': 'A · 研究型教席（推断）',
    'B': 'B · 可能为教席',
    'C': 'C · 其他研究人员',
}


def domain_of(topics):
    """topics: list of dicts with 'name'.

    Keywords must start a word: plain substring matching made 'art' fire inside
    'particle' and 'data' inside 'mandate', which silently mislabelled people.
    """
    if not topics:
        return 'other'
    tl = ' '.join((t.get('name') or '') for t in topics).lower()
    for pref, dom in TOPIC_RULES:
        if re.search(r'(?<![a-z])' + re.escape(pref.lower()), tl):
            return dom
    return 'other'


def classify(works, span):
    """Research-faculty heuristic shared by all OpenAlex-based universities."""
    if span >= 12 and works >= 12:
        return 'A'
    if span >= 9 and works >= 8:
        return 'B'
    return 'C'
