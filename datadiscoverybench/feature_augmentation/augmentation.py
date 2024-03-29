import pandas as pd
from sklearn.model_selection import train_test_split
from autogluon.tabular import TabularDataset, TabularPredictor
from sklearn.metrics import mean_squared_error, r2_score
import duckdb
import time
from datadiscoverybench.utils import load_dresden_db
from datadiscoverybench.utils import load_git_tables_db
from datadiscoverybench.feature_augmentation.imdb.IMDB_Dataset import IMDB

def augment(con: duckdb.DuckDBPyConnection, df: pd.DataFrame, column_name: str, id_column_name: str) -> pd.DataFrame:
    result = con.execute('''
                            SELECT df.*, 
                                   TEMPT1.Feature 
                            FROM df
                            LEFT JOIN (
                                SELECT df.''' + column_name + ''', 
                                       Count(*) AS Feature 
                                FROM df 
                                LEFT JOIN AllTables 
                                ON df.''' + column_name + '''=AllTables.CellValue 
                                GROUP BY df.''' + column_name + '''
                            ) AS TEMPT1 
                            ON df.''' + column_name + '''=TEMPT1.''' + column_name + '''
                            ORDER BY df.''' + id_column_name + ''' ASC;
                         ''').fetch_df()

    return result

def main():
    dataset = IMDB(number_rows=1000)
    data = dataset.get_df()

    y = data['averageRating'].values
    data.drop(['averageRating'], axis=1, inplace=True, errors='ignore')

    con = duckdb.connect(database=':memory:')
    #load_dresden_db(con, parts=[0,1])
    load_git_tables_db(con)

    # augment

    length_before = len(data)
    augmentation_time_start = time.time()
    #data = augment(con, data, column_name='originalTitle', id_column_name=dataset.id_column_name)
    augmentation_time = time.time() - augmentation_time_start
    assert length_before == len(data), "There number of rows is different after augmentation"
    print(data.columns)

    data.drop([dataset.id_column_name], axis=1, inplace=True, errors='ignore')

    print('head')
    print(data.head().values)

    X = data.values

    X_train, X_test, y_train, y_test = train_test_split(X, y, train_size=0.6, random_state=42)

    df = pd.DataFrame(data=X_train)
    label = 'class'
    df[label] = y_train
    my_data_train = TabularDataset(data=df)

    df_test = pd.DataFrame(data=X_test)
    my_data_test = TabularDataset(data=df_test)

    predictor = TabularPredictor(label=label, problem_type='regression').fit(train_data=my_data_train,
                                                                             time_limit=5 * 60)
    predictions = predictor.predict(my_data_test)

    print('r2 score: ' + str(r2_score(y_test, predictions)))
    print('mean_squared_error: ' + str(mean_squared_error(y_test, predictions, squared=False)))
    print('augmentation time: ' + str(augmentation_time))

if __name__ == "__main__":
    main()