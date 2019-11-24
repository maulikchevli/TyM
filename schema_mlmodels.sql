drop table if exists ml_models;
    create table ml_models (
    id integer primary key autoincrement,
    username text not null,
    model_name text not null,
    model_algo text not null,
    filename text not null,
    performance_measure text not null
);
