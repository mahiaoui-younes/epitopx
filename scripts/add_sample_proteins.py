#!/usr/bin/env python
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from api.models import Protein
from django.contrib.auth import get_user_model
User = get_user_model()
admin = User.objects.filter(username='admin1').first()

proteins = [
    dict(
        name='TaMs1 (AAB60239)',
        sequence='MLSRTTLKFLYLSFFVISSVNAANEDEKKKEEKKDVVLDVTATSCENVTFDTRDPNAVVLTVKEGHRFKTLKVGEKTLFNVDTSKHTPVKALKLKHESDEWFRLDLHAAQPKMFKKKGDKEYSESKFETYYDEVLFKGKSAKELDVSKFEDPALFTSANFGTGKKYTFKKDFKPSKVLFEKKEVGKPNNAKYLEVVVFVGSDSKKVVRLDYFYTGDSRLKETYFELKDDKWVQMSQADANKALNAMDSNWSSDYKPVVDKFSPLAVFASVLIVFSSVLYFL',
        organism='Theileria annulata',
        description='Merozoite surface antigen Tams1 — major vaccine candidate against tropical theileriosis',
        is_public=True,
    ),
    dict(
        name='Tp2 Surface Antigen',
        sequence='MKVLSLLVLAFAASAVQAQTPAEVSQHISSQLSGKSVNLTSATSQPLSSNKSTLSSVSGQTPTSKPAQNLSTTSGPQQVTPTSQASAQKASTVTQSPTQPATTAAPAASATPASVSTQAPAQSQAQVTQQAPAQVSQAQTQSQQNQVTPQVQTQAQVTPQAQVTPQSQATPQVQTPAQVTPQAQVTPQAQVTPQAQVTPQ',
        organism='Theileria parva',
        description='Surface antigen Tp2 — major cytotoxic T-cell target in East Coast Fever',
        is_public=True,
    ),
    dict(
        name='SpA Surface Protein A',
        sequence='MGKIEEGKLVIWINGDKGYNGLAEVGKKFEKDTGIKVTVEHPDKLEEKFPQVAATGDGPDIIFWAHDRFGGYAQSGLLAEITPDKAFQDKLYPFTWDAVRYNGKLIAYPIAVEALSLIYNKDLLPNPPKTWEEIPALDKELKAKGKSALMFNLQEPYFTWPLIAADGGYAFKYENGKYDIKDVGVDNAGAKAGLTFLVDLIKNKHMNADTDYSIAEAAFNKGETAMTINGPWAWSNIDTSKVNYGVTVLPTFKGQPSKPFVGQLWLSAEQTQALSGQGAVAQAAATQLQAKQVQQ',
        organism='Theileria annulata',
        description='Surface protein A — involved in complement evasion and host immune modulation',
        is_public=True,
    ),
    dict(
        name='TaGAP50 (Rhoptry)',
        sequence='MKSKSPLMMVIVALSLIAVVSASEDEDIDDDDDDDDIENPSDEDSDIESDEFSDDEDFDTDSEDEDYDEEDEDEDEDEDEDDEDEDEDDEDEDEDDEDEDEDDEDEDEDDEDEDEDDEDEDEDDEDEDEDDEDEDEDDEDEDEDDEDEDDEDEDEDDEDEDEDDEDEDEDDEDEDEDDEDEDDEDEDEDDEDEDEDDEDEDEDDEDEDDEDEDEDDEDEDEDDEDEDD',
        organism='Theileria annulata',
        description='Gliding-associated protein 50 — rhoptry protein essential for host-cell invasion',
        is_public=True,
    ),
    dict(
        name='PfEMP1-like Variant Ag',
        sequence='MKLVLLLVTLAFAASADAIAASQPNASPQPNAAPQPNAAPQPNAAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAP',
        organism='Plasmodium falciparum',
        description='PfEMP1-like variant surface antigen — target of protective immunity',
        is_public=True,
    ),
]

created = 0
for p in proteins:
    if not Protein.objects.filter(name=p['name']).exists():
        Protein.objects.create(created_by=admin, **p)
        created += 1
        print('  Added:', p['name'])
    else:
        print('  Exists:', p['name'])

print('\nDone -', created, 'proteins added')
