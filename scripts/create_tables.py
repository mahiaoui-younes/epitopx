import MySQLdb

conn = MySQLdb.connect(user='root', host='127.0.0.1')
cursor = conn.cursor()

# Créer la base de données si elle n'existe pas
cursor.execute('CREATE DATABASE IF NOT EXISTS backend_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
cursor.execute('USE backend_db')

# Créer la table Protein
cursor.execute('''
CREATE TABLE IF NOT EXISTS protein (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    fullname VARCHAR(500) NOT NULL,
    sequence LONGTEXT NOT NULL,
    organism VARCHAR(200) NOT NULL,
    description LONGTEXT NOT NULL,
    pdp_file VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
''')

# Créer la table DNA
cursor.execute('''
CREATE TABLE IF NOT EXISTS dna_sequence (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    sequence LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
''')

# Créer la table ProteinConversion
cursor.execute('''
CREATE TABLE IF NOT EXISTS protein_conversion (
    id INT AUTO_INCREMENT PRIMARY KEY,
    original_dna LONGTEXT NOT NULL,
    rna LONGTEXT NOT NULL,
    protein LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
''')

# Créer la table Article
cursor.execute('''
CREATE TABLE IF NOT EXISTS article (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titre VARCHAR(200) NOT NULL,
    contenu LONGTEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
''')

conn.commit()
print('✅ Tous les tableaux ont été créés avec succès dans MySQL!')
print('   - protein')
print('   - dna_sequence')
print('   - protein_conversion')
print('   - article')
conn.close()
