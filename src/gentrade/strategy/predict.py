import timesfm
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt


def create_sample_dataframe(
    start_date: datetime, end_date: datetime, freq: str = "D"
) -> pd.DataFrame:
    """
    Create a sample DataFrame with time series data.

    Args:
        start_date (datetime): Start date of the time series.
        end_date (datetime): End date of the time series.
        freq (str): Frequency of the time series (default: "D" for daily).

    Returns:
        pd.DataFrame: DataFrame with columns 'unique_id', 'ds', and 'ts'.
    """
    date_range = pd.date_range(start=start_date, end=end_date, freq=freq)
    print(date_range)
    ts_data = np.random.randn(len(date_range))
    df = pd.DataFrame({"unique_id": "ts-1", "ds": date_range, "ts": ts_data})
    return df

def get_model(mode_version="2.0"):
    model = timesfm.TimesFm(
        hparams=timesfm.TimesFmHparams(
            backend="gpu",
            per_core_batch_size=32,
            horizon_len=128,
            num_layers=50,
            context_len=2048,
        ),
        checkpoint=timesfm.TimesFmCheckpoint(
            huggingface_repo_id="google/timesfm-2.0-500m-pytorch"),
        )

    return model


import hvplot
import hvplot.pandas


def start():
    pd.options.plotting.backend = 'hvplot'
    pd.set_option('plotting.backend', 'hvplot')
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=10)
    df = create_sample_dataframe(start_dt, end_dt)
    print(df)
    model = get_model()
    forecast_df = model.forecast_on_df(
        inputs=df,
        freq='D',
        value_name='ts'
    )
    new = df[['ds', 'ts']].copy()
    print(forecast_df.columns)
    print(forecast_df)
    forecast_df.plot(backend='matplotlib', kind='scatter', x='ds', y='timesfm')
    #plt.plot(forecast_df['timesfm'])
    new2 = forecast_df[['ds', 'timesfm']].copy()
    new2 = new2.rename(columns={'timesfm': 'ts'})
    new3 = pd.concat([new, new2])
    print(new3)
    plt.bar(new3['ds'], new3['ts'])
    plt.show()

if __name__ == "__main__":
    start()