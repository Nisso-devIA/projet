module.exports = {
  apps: [
    {
      name: "wado-osny",
      cwd: "/var/www/wado-osny",
      script: "node_modules/next/dist/bin/next",
      args: "start -H 127.0.0.1 -p 3003",
      env: {
        NODE_ENV: "production",
        PORT: "3003",
        HOSTNAME: "127.0.0.1",
      },
    },
  ],
};
