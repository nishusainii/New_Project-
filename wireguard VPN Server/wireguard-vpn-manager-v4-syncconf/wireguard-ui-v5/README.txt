Replace only these two files in the existing V4 project:
  app/templates/index.html
  app/static/style.css

Then rebuild:
  sudo docker-compose up -d --build
  sudo docker-compose logs --tail=50 app

This UI remains compatible with the existing dry-run backend variables and routes.
