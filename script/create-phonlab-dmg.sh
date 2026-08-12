brew install create-dmg

SOURCE_PATH=$1
OUT_PATH="${2:-Phonlab-Installer.dmg}"

echo "Creating DMG from $SOURCE_PATH"

create-dmg \
    --volname "Phonlab Installer" \
    --window-pos 200 120 \
    --window-size 600 400 \
    --icon-size 100 \
    --icon "Phonlab.app" 200 190 \
    --hide-extension "Phonlab.app" \
    --app-drop-link 400 185 \
    --hdiutil-quiet \
    $OUT_PATH \
    $SOURCE_PATH
