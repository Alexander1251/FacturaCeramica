from django.db import connection
print(connection.introspection.table_names())
