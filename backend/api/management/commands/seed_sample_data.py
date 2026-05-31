"""Management command: seed the database with sample proteins (idempotent)."""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

SAMPLE_PROTEINS = [
    dict(
        name='TaMs1 Surface Antigen',
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
        name='PfMSP1 Merozoite Surface Protein',
        sequence='MKLVLLLVTLAFAASADAIAASQPNASPQPNAAPQPNAAPQPNAAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAPQPNAP',
        organism='Plasmodium falciparum',
        description='Merozoite surface protein 1 — key target of protective humoral immunity in malaria',
        is_public=True,
    ),
    dict(
        name='TgSAG1 Surface Antigen',
        sequence='MVKSNGGCVDAALLAACTLLAANAAAVPAGEPKVHDGSPPEGRSEGQHPNAAEGADVSAELKNKAILESATSAQLVKSSDRELLQERQGFVGEASVLPGGQSAHEAQEAQIAQPSEALKQAIKEAQSAAEAAQAQLKEAEKAAQEAQAAAKAAETAQKAAEAAQAAQAAAKAAKAAEAAQEAQAAAKAAETAQKAAEAAQAAQAAAKAAKAAEAAQEAQ',
        organism='Toxoplasma gondii',
        description='SAG1 (p30) major surface antigen — dominant antigen in primary toxoplasmosis',
        is_public=True,
    ),
    dict(
        name='BbMSA-2c Merozoite Antigen',
        sequence='MKVLSVLLAVALVANAQDQATPSEGSPASTTTKETAASTTTTSSTTSTTTTTSSTSTTASSTTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSSSTSTTSS',
        organism='Babesia bovis',
        description='Merozoite surface antigen 2c — vaccine candidate against bovine babesiosis',
        is_public=True,
    ),
]


class Command(BaseCommand):
    help = 'Seed the database with sample proteins (idempotent).'

    def handle(self, *args, **options):
        from api.models import Protein

        # Get or find a suitable owner (prefer superuser)
        owner = User.objects.filter(is_superuser=True).first()
        if not owner:
            owner = User.objects.first()
        if not owner:
            self.stdout.write(self.style.WARNING('No users found — skipping sample data.'))
            return

        created = 0
        for data in SAMPLE_PROTEINS:
            _, was_created = Protein.objects.get_or_create(
                name=data['name'],
                defaults={**data, 'created_by': owner},
            )
            if was_created:
                created += 1
                self.stdout.write(f'  + {data["name"]}')

        self.stdout.write(self.style.SUCCESS(
            f'Sample data: {created} proteins added, {len(SAMPLE_PROTEINS) - created} already existed.'
        ))
