drop table if exists users;
    create table users (
    id integer primary key autoincrement,
	user_type text default "std",
    fullname text not null,
    address text not null,
    username text not null,
    email text not null,
    password text not null
);
