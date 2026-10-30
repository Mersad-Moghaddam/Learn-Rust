from django.db import migrations


def add_constraints(apps, schema_editor):
    if schema_editor.connection.vendor != "mysql":
        return
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT CHARACTER_SET_NAME, COLLATION_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s",
            ["account_emailaddress", "email"],
        )
        charset, collation = cursor.fetchone()
    quote = schema_editor.quote_name
    schema_editor.execute(
        "ALTER TABLE account_emailaddress "
        "ADD COLUMN accounts_verified_email varchar(254) CHARACTER SET %s COLLATE %s "
        "GENERATED ALWAYS AS (CASE WHEN verified THEN email ELSE NULL END) STORED, "
        "ADD COLUMN accounts_primary_user bigint GENERATED ALWAYS AS "
        "(CASE WHEN `primary` THEN user_id ELSE NULL END) STORED, "
        "ADD UNIQUE INDEX accounts_unique_verified_email (accounts_verified_email), "
        "ADD UNIQUE INDEX accounts_unique_primary_user (accounts_primary_user)"
        % (quote(charset), quote(collation))
    )


def remove_constraints(apps, schema_editor):
    if schema_editor.connection.vendor == "mysql":
        schema_editor.execute(
            "ALTER TABLE account_emailaddress "
            "DROP INDEX accounts_unique_verified_email, DROP INDEX accounts_unique_primary_user, "
            "DROP COLUMN accounts_verified_email, DROP COLUMN accounts_primary_user"
        )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("accounts", "0001_initial"),
        ("account", "0009_emailaddress_unique_primary_email"),
    ]

    operations = [migrations.RunPython(add_constraints, remove_constraints, atomic=False)]
