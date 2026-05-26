#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import DNASequence, Protein

# Ajouter la séquence ADN
dna_sequence = "atgttgtccaggaccaccctcaagttcttatatttgagcttcttcgttatctcatccgttaatgctgcaaatgaggatgaaaagaaaaaggaagaaaaaaaagatgttgttcttgatgttactgccacttcatgtgagaatgttacctttgatactcgcgaccctaatgccgtggtattaactgtcaaggaaggccaccgtttcaagacccttaaggtcggagaaaagactttattcaatgttgacacctcaaaacataccccagttaaggcattaaaacttaagcatgagtcagatgagtggttcaggcttgatcttcatgctgcccaaccaaagatgttcaagaagaagggagacaaggaatattctgagtccaaattcgagacctactacgatgaagtcttgttcaagggaaaatccgccaaggaactagatgtttccaagttcgaagatccagctttgttcacctccgctaacttcggcactggaaagaagtacacctttaaaaaggatttcaaaccttccaaagttctcttcgagaagaaagaagttggaaaacccaacaatgccaagtatcttgaagttgttgtctttgttggttctgattccaagaaggtcgtcagactcgactacttctataccggtgactcaaggttaaaggagacctacttcgagcttaaggacgacaagtgggttcaaatgtcacaggcagatgcaaacaaggccttgaatgccatggactcaaactggtcatccgattacaaaccagttgtcgacaagttctccccccttgcagtcttcgcctcagtactcatcgtcttctcatcagtcctttacttcctt"

# Vérifier si la séquence n'existe pas déjà
if not DNASequence.objects.filter(sequence=dna_sequence).exists():
    dna_obj = DNASequence.objects.create(
        name="U22888.1 Theileria annulata merozoite surface glycoprotein Tams1",
        sequence=dna_sequence
    )
    print(f"✅ Séquence ADN ajoutée: {dna_obj.name}")
else:
    print("⚠️ Séquence ADN déjà existe dans la base")

# Ajouter la protéine
protein_sequence = "MLSRTTLKFLYLSFFVISSVNAANEDEKKKEEKKDVVLDVTATSCENVTFDTRDPNAVVLTVKEGHRFKTLKVGEKTLFNVDTSKHTPVKALKLKHESDEWFRLDLHAAQPKMFKKKGDKEYSESKFETYYDEVLFKGKSAKE LDVSKFEDPALFTSANFGTGKKYTFKKDFKPSKVLFEKKEVGKPNNAKYLEVVVFVGSDSKKVVRLDYFYTGDSRLKETYFELKDDKWVQMSQADANKALNAMDSNWSSDYKPVVDKFSPLAVFASVLIVFSSVLYFL"

if not Protein.objects.filter(sequence=protein_sequence).exists():
    protein_obj = Protein.objects.create(
        name="AAB60239.1",
        fullname="merozoite surface glycoprotein",
        sequence=protein_sequence,
        organism="Theileria annulata",
        description="Merozoite surface glycoprotein from Theileria annulata",
        pdp_file=""
    )
    print(f"✅ Protéine ajoutée: {protein_obj.name}")
else:
    print("⚠️ Protéine déjà existe dans la base")

print("\n✅ Données d'exemple ajoutées avec succès!")
