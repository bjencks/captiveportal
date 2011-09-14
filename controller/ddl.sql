-- This is sqlite3 ddl, don't try to use it for any other dbms
CREATE TABLE user_sessions (
  id INTEGER PRIMARY KEY,
  user TEXT NOT NULL,
  mac BLOB NOT NULL,
  start timestamp,
  end timestamp
);

CREATE TABLE addr_sessions (
  id INTEGER PRIMARY KEY,
  user_session INTEGER,
  mac BLOB,
  source TEXT, -- arp, nd, radius, or dhcp
  ipv4 BLOB,
  ipv6 BLOB,
  start timestamp,
  end timestamp,
  FOREIGN KEY (user_session) REFERENCES user_sessions(id)
);
