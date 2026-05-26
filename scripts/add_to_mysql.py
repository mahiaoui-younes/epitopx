import MySQLdb

conn = MySQLdb.connect(user='root', host='127.0.0.1', database='backend_db')
cursor = conn.cursor()

# Les séquences à ajouter
sequences = [
    {
        'name': 'U22888.1 Theileria annulata merozoite surface glycoprotein Tams1',
        'sequence': 'atgttgtccaggaccaccctcaagttcttatatttgagcttcttcgttatctcatccgttaatgctgcaaatgaggatgaaaagaaaaaggaagaaaaaaaagatgttgttcttgatgttactgccacttcatgtgagaatgttacctttgatactcgcgaccctaatgccgtggtattaactgtcaaggaaggccaccgtttcaagacccttaaggtcggagaaaagactttattcaatgttgacacctcaaaacataccccagttaaggcattaaaacttaagcatgagtcagatgagtggttcaggcttgatcttcatgctgcccaaccaaagatgttcaagaagaagggagacaaggaatattctgagtccaaattcgagacctactacgatgaagtcttgttcaagggaaaatccgccaaggaactagatgtttccaagttcgaagatccagctttgttcacctccgctaacttcggcactggaaagaagtacacctttaaaaaggatttcaaaccttccaaagttctcttcgagaagaaagaagttggaaaacccaacaatgccaagtatcttgaagttgttgtctttgttggttctgattccaagaaggtcgtcagactcgactacttctataccggtgactcaaggttaaaggagacctacttcgagcttaaggacgacaagtgggttcaaatgtcacaggcagatgcaaacaaggccttgaatgccatggactcaaactggtcatccgattacaaaccagttgtcgacaagttctccccccttgcagtcttcgcctcagtactcatcgtcttctcatcagtcctttacttcctt'
    }
]

for seq in sequences:
    # Vérifier si la séquence existe déjà
    cursor.execute('SELECT id FROM dna_sequence WHERE sequence = %s', (seq['sequence'],))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO dna_sequence (name, sequence) VALUES (%s, %s)',
            (seq['name'], seq['sequence'])
        )
        print(f"✅ Ajoutée: {seq['name']}")
    else:
        print(f"⚠️  Déjà existe: {seq['name']}")

conn.commit()
print('\n✅ Données ajoutées à MySQL!')
conn.close()
