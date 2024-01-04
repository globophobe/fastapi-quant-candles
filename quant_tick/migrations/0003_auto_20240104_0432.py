# Generated by Django 5.0.1 on 2024-01-04 04:32

from django.db import migrations, models

import quant_tick.models.trades


class Migration(migrations.Migration):
    dependencies = [
        (
            "quant_tick",
            "0002_rename_should_aggregate_trades_symbol_aggregate_trades_and_more",
        ),
    ]

    operations = [
        migrations.AlterField(
            model_name="symbol",
            name="code_name",
            field=models.SlugField(
                max_length=255, unique=True, verbose_name="code name"
            ),
        ),
        migrations.RenameField(
            model_name="tradedata",
            old_name="file_data",
            new_name="filtered_data",
        ),
        migrations.AlterField(
            model_name="tradedata",
            name="filtered_data",
            field=models.FileField(
                blank=True,
                upload_to=quant_tick.models.trades.upload_filtered_data_to,
                verbose_name="filtered data",
            ),
        ),
        migrations.AddField(
            model_name="tradedata",
            name="aggregated_data",
            field=models.FileField(
                blank=True,
                upload_to=quant_tick.models.trades.upload_aggregated_data_to,
                verbose_name="aggregated data",
            ),
        ),
        migrations.AddField(
            model_name="tradedata",
            name="candle_data",
            field=models.FileField(
                blank=True,
                upload_to=quant_tick.models.trades.upload_candle_data_to,
                verbose_name="candle data",
            ),
        ),
        migrations.AddField(
            model_name="tradedata",
            name="clustered_data",
            field=models.FileField(
                blank=True,
                upload_to=quant_tick.models.trades.upload_clustered_data_to,
                verbose_name="clustered data",
            ),
        ),
        migrations.AddField(
            model_name="tradedata",
            name="raw_data",
            field=models.FileField(
                blank=True,
                upload_to=quant_tick.models.trades.upload_raw_data_to,
                verbose_name="raw data",
            ),
        ),
        migrations.AlterField(
            model_name="tradedata",
            name="frequency",
            field=models.PositiveIntegerField(
                choices=[(1, "Minute"), (60, "Hour"), (1440, "Day")],
                db_index=True,
                verbose_name="frequency",
            ),
        ),
        migrations.DeleteModel(
            name="TradeDataSummary",
        ),
        migrations.AlterUniqueTogether(
            name="tradedata",
            unique_together={("symbol", "timestamp", "frequency")},
        ),
    ]
