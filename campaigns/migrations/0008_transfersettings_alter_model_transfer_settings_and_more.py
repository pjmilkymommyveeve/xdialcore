# campaigns/migrations/0008_transfersettings_alter_model_transfer_settings_and_more.py

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('campaigns', '0007_remove_campaignrequirements_idx_campaign_requirements_name_and_more'),  # Replace with your actual previous migration
    ]

    operations = [
        # Step 1: Create the TransferSettings model
        migrations.CreateModel(
            name='TransferSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
            ],
            options={
                'verbose_name': 'Transfer Setting',
                'verbose_name_plural': 'Transfer Settings',
                'db_table': 'transfer_settings',
                'indexes': [
                    models.Index(fields=['name'], name='idx_transfer_settings_name'),
                ],
            },
        ),
        
        # Step 2: Rename old field
        migrations.RenameField(
            model_name='model',
            old_name='transfer_settings',
            new_name='transfer_settings_old',
        ),
        
        # Step 3: Add new FK field
        migrations.AddField(
            model_name='model',
            name='transfer_settings',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='models',
                to='campaigns.transfersettings'
            ),
        ),
        
        # Step 4: Add index
        migrations.AddIndex(
            model_name='model',
            index=models.Index(fields=['transfer_settings'], name='idx_models_transfer_settings'),
        ),
        
        # Step 5: Remove old field
        migrations.RemoveField(
            model_name='model',
            name='transfer_settings_old',
        ),
    ]