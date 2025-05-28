from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
import os
import yaml

with open("/app/config.yaml") as f:
    cfg = yaml.load(f, Loader=yaml.FullLoader)


engine = create_engine(f"sqlite:///{os.path.join(cfg['sql_alchemy']['loc'], cfg['sql_alchemy']['db'])}") 
Base = declarative_base() 