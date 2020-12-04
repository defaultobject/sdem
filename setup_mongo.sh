mongo <<EOF
use sacred;
db.createUser(
  {
    user: "default",
    pwd: "default",
    roles: [ { role: "userAdminAnyDatabase", db: "admin" } ]
  }
);
EOF
