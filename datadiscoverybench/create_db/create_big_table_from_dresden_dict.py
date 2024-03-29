import duckdb
import glob
import pandas as pd
import gzip
import json
import pickle
import sys
import zlib

#path = '/home/mahdi/DWTC_json'
#my_path = '/home/felix/duckdb'

path = '/home/neutatz/Software/DataDiscoveryBenchmark/data/dresden'
my_path = '/home/neutatz/Software/DataDiscoveryBenchmark/data'

table_id = 0
cell_value_id_counter = 0
cell_value2id = {}

data = []
#download http://wwwdb.inf.tu-dresden.de/misc/dwtc/data_feb15/dwtc-000.json.gz
for zip_path in glob.glob(path + "/*.json.gz"):

    cell_values = []
    table_ids = []
    column_ids = []
    row_ids = []

    with gzip.open(zip_path, 'rt') as f:
        for line in f:
            json_data = json.loads(line)

            #print(json_data)

            #todo fix table header situation
            for row_id in range(len(json_data['relation'])):
                for column_id in range(len(json_data['relation'][0])):
                    cell_value = str(json_data['relation'][row_id][column_id])
                    #cell_value = zlib.compress(cell_value.encode())

                    if not cell_value in cell_value2id:
                        cell_value2id[cell_value] = cell_value_id_counter
                        cell_value_id_counter += 1
                    cell_values.append(cell_value2id[cell_value])
                    table_ids.append(table_id)
                    column_ids.append(column_id)
                    row_ids.append(row_id)
            table_id += 1

    d = {'CellValue': cell_values, 'TableId': table_ids, 'ColumnId': column_ids, 'RowId': row_ids}
    df = pd.DataFrame(data=d)

    df['CellValue'] = df['CellValue'].astype('uint32')
    df['TableId'] = df['TableId'].astype('uint32')
    df['ColumnId'] = df['ColumnId'].astype('uint32')
    df['RowId'] = df['RowId'].astype('uint32')
    df.to_parquet(my_path + '/dresden/import/' + zip_path.split('/')[-1].split('.')[0] + '.parquet')


pickle.dump(cell_value2id, open(my_path + '/dresden/import/dict.pickle', 'wb+'))

dumped_obj = pickle.dumps(cell_value2id)
pipeline_size = sys.getsizeof(dumped_obj)
print('size:' + str(pipeline_size))

con = duckdb.connect(database=':memory:')
con.execute("CREATE TABLE AllTables(CellValue UINTEGER, TableId UINTEGER, ColumnId USMALLINT, RowId UINTEGER);")
con.execute("INSERT INTO AllTables SELECT * FROM read_parquet('" + my_path + "/dresden/import/*.parquet');")
con.execute("CREATE INDEX token_idx ON AllTables (CellValue);")
con.execute("EXPORT DATABASE '" + my_path + "/dresden/db/' (FORMAT PARQUET);")