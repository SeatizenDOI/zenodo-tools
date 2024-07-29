import os
import psutil
from datetime import datetime
from dataclasses import dataclass, field

from .base_model import AbstractBaseDAO

@dataclass
class StatisticSQLDTO():
    name: str
    seq: int

@dataclass
class StatisticSQLDAO(AbstractBaseDAO):
    table_name = "sqlite_sequence"

    statistic: list[StatisticSQLDTO] = field(default_factory=list)

    def __post_init__(self) -> None:
        query = f""" SELECT name, seq
                     FROM {self.table_name}
                 """
        results = self.sql_connector.execute_query(query) 
        if len(results) == 0:
            print("[WARNING] Cannot get stats.")

        for name, sequence in results:

            self.statistic.append(StatisticSQLDTO(
                name=name,
                seq=sequence
            ))

class Benchmark:
    
    def __init__(self) -> None:
        self.t_start, self.t_stop = None, None
    
    def start(self) -> None: 
        self.t_start = datetime.now()
    
    def stop(self) -> None:
        self.t_stop = datetime.now()
    
    def show(self, word="") -> None:
        if self.t_start == None or self.t_stop == None: return
        print(f"\n{word} - Elapsed time: {self.t_stop - self.t_start} sec")
        print(f"Memory usage: {round(psutil.Process(os.getpid()).memory_info().rss / 1024 ** 3, 2)} GiB\n")
    
    def stop_and_show(self, word=""):
        self.stop()
        self.show(word)