# https://github.com/phiresky/sql.js-httpvfs/blob/master/create_db.sh

set -eu

indb="$1"
outdir="$2"

# for chunked mode, we need to know the database size in bytes beforehand
bytes="$(stat --printf="%s" "$indb")"
# set chunk size to 10MiB (needs to be a multiple of the `pragma page_size`!)
serverChunkSize=$((25 * 1024 * 1024))
suffixLength=3
rm -f "$outdir/tp."*
split "$indb" --bytes=$serverChunkSize "$outdir/tp." --suffix-length=$suffixLength --numeric-suffixes

# set request chunk size to match page size
requestChunkSize="$(sqlite3 "$indb" 'pragma page_size')"

# write a json config
echo '
{
    "serverMode": "chunked",
    "requestChunkSize": '$requestChunkSize',
    "databaseLengthBytes": '$bytes',
    "serverChunkSize": '$serverChunkSize',
    "urlPrefix": "tp.",
    "suffixLength": '$suffixLength'
}
' >"$outdir/config.json"
