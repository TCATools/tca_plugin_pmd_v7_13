set -x

export CURRENT=$(cd "$(dirname "$0")";pwd)
export SOURCE_DIR="${CURRENT}/src"
export SCAN_FILES="${CURRENT}/filelist.txt"
export RESULT_DIR="${CURRENT}/workdir/out"
export TASK_REQUEST="${CURRENT}/task_request.json"

echo $SOURCE_DIR
echo $RESULT_DIR

# echo "- * - * - * - * - * - * - * - * - * - * - * - * -* -* -* -* -* -* -"
python3 ${CURRENT}/../src/main.py check

echo "- * - * - * - * - * - * - * - * - * - * - * - * -* -* -* -* -* -* -"
python3 ${CURRENT}/../src/main.py scan 2>&1 | tee ${CURRENT}/run.log
echo "- * - * - * - * - * - * - * - * - * - * - * - * -* -* -* -* -* -* -"
