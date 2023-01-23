cd "$(dirname "$0")"

cd ../..

# conda create -y -n scrape python=3.9

source ~/.bashrc

nvm install v19.4.0

if [ ! -d ]; then 
( cd js && npx create-react-app scrape_frontend )
fi
