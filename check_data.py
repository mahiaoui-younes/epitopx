import os
import django
os.environ['DATABASE_URL'] = 'postgresql://epitopx:epitopx2024@localhost:5432/backend_db'
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
import sys
sys.path.insert(0, r'c:\Users\asus\Documents\flutter_project\univ\all=epitopX\backend')
django.setup()

from api.models import Protein, Epitope

print('=== PROTEINS ===')
for p in Protein.objects.all():
    ecount = p.epitopes.count() if hasattr(p, 'epitopes') else '?'
    print(f'  ID={p.id} | {p.name[:60]} | org={p.organism} | public={p.is_public} | ep={ecount}')

print()
print('=== EPITOPES (first 15) ===')
for e in Epitope.objects.all()[:15]:
    fields = [f.name for f in e._meta.fields]
    seq = getattr(e, 'sequence', getattr(e, 'peptide', '?'))
    score = getattr(e, 'score', getattr(e, 'prediction_score', '?'))
    print(f'  ID={e.id} | protein_id={e.protein_id} | score={score} | seq={str(seq)[:35]}')
print(f'Total epitopes: {Epitope.objects.count()}')
print()
print('Epitope fields:', [f.name for f in Epitope._meta.fields])
print('Protein fields:', [f.name for f in Protein._meta.fields])
