# Step 1: Download assets
docker run --rm -v "$PWD:/workspace" -w /workspace node:12-alpine sh -c '
  export npm_config_cache="/workspace/node_cache"
  for dir in assets_src/*/; do
    dir="${dir%/}"
    [ -f "$dir/package.json" ] || { echo ".. skip $dir" ; continue; }
    echo ">> Building and installing assets package ${dir##*/}"
    ( cd "$dir" && npm install --unsafe-perm )
  done
'

# Step 2: Compile sass
docker run --rm -v "$PWD:/workspace" -w /workspace apluslms/develop-sass:1 \
  sass --style=compressed assets/sass:assets/css
