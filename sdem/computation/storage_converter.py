from sacred.observers import FileStorageObserver, MongoObserver
from sacred.dependencies import MB
import seml

import json
import gridfs
import datetime
import dateutil.parser

import os

from .. import state


def mongo_db_to_file_storage(
    project_dir: str, basedir: str, _id: int, overwrite: bool = False
):
    collection = seml.database.get_collection(basedir)

    # setup mongo filestorage
    mongodb_config = seml.database.get_mongodb_config()
    db = seml.database.get_database(**mongodb_config)

    fs = gridfs.GridFS(db)

    runs = collection.find({})
    for run in runs:

        _id = run["_id"]
        # cache original _id
        insert_id = _id

        if not overwrite:
            # if not overwritting then we need to get the max id in basedir/
            dirs = os.listdir(basedir)
            max_id = max([int(d) for d in dirs if d.isdigit()])
            _id = max_id + 1
            run["_id"] = _id

        run_root = "{base}/{_id}".format(base=basedir, _id=_id)

        if overwrite:
            remove_dir_if_exists(run_root)

        os.mkdir(run_root)

        config = {}
        if "config" in run.keys():
            config = run["config"]

        captured_out = ""
        if "captured_out" in run.keys():
            captured_out = run["captured_out"]

        metrics = {}
        if "metrics" in run.keys():
            metrics = run["metrics"]

        remove_keys_for_run_file = ["config", "captured_out", "metrics"]
        run_dict = {k: v for k, v in run.items() if k not in remove_keys_for_run_file}

        # if artifacts save in same folder
        if "artifacts" in run.keys() and len(run["artifacts"]) > 0:
            new_artifacts = []
            for artifact in run["artifacts"]:
                a = artifact["name"]
                db_filename = "artifact://{}/{}/{}".format(basedir, insert_id, a)
                db_id = artifact["file_id"]

                if fs.exists(db_id):
                    with open(run_root + "/" + a, "wb") as f:
                        f.write(fs.get(db_id).read())

                    new_artifacts.append(a)
                else:
                    print("{f} does not exist -- igoring!".format(f=db_filename))

            run["artifacts"] = new_artifacts

        # if experiment sources save in _sources
        if "experiment" in run.keys() and "sources" in run["experiment"].keys():
            new_sources = []
            for source in run["experiment"]["sources"]:
                name = source[0]
                source_id = source[1]

                if fs.exists(source_id):
                    file_bytes = fs.get(source_id)

                    md5sum = get_digest_from_bytes(file_bytes)

                    file_bytes = fs.get(source_id)
                    source_name, ext = os.path.splitext(os.path.basename(name))
                    store_name = source_name + "_" + md5sum + ext
                    with open(basedir + "/_sources/" + store_name, "wb") as f:
                        f.write(file_bytes.read())

                    new_sources.append([name, "/_sources/" + store_name])

                run["experiment"]["sources"] = new_sources

        # convert dates to strings
        date_keys = ["stop_time", "heartbeat", "start_time"]
        for k in date_keys:
            run[k] = str(run[k])

        # save files
        with open(run_root + "/run.json", "w") as f:
            json.dump(run, f)

        with open(run_root + "/config.json", "w") as f:
            json.dump(config, f)

        with open(run_root + "/metrics.json", "w") as f:
            json.dump(metrics, f)

        with open(run_root + "/cout.txt", "w") as f:
            f.write(captured_out)


def file_storage_to_mongo_db(
    project_dir: str,
    collection,
    basedir: str,
    _id: int,
    insert_id: int,
    overwrite: bool = True,
    error_entry=False,
):
    """
    Converts a saved file storage run into a mongo db run. If overwrite then it checks
        if config id is already in mongo db and then overwrites that DB entry. Else it appends with a new id.
    """
    if (overwrite is False) or (insert_id is None):
        max_id = seml.database.get_max_in_collection(collection, "_id")

        if max_id is None:
            insert_id = 1
        else:
            insert_id = max_id + 1

    if insert_id is not None:
        insert_id = int(insert_id)
    if _id is not None:
        _id = int(_id)

    if False and overwrite and (insert_id is not None):
        observed = MongoObserver(overwrite=insert_id)
    else:
        observed = MongoObserver()

    get_fp = lambda f: "{basedir}/{_id}/{f}".format(basedir=basedir, _id=_id, f=f)

    with open(get_fp("config.json")) as f:
        config_file = json.load(f)
    with open(get_fp("metrics.json")) as f:
        metrics_file = json.load(f)
    with open(get_fp("run.json")) as f:
        run_file = json.load(f)
    with open(get_fp("cout.txt")) as f:
        cout_file = f.read()

    final_d = {}

    final_d.update({"config": config_file})
    final_d.update({"metrics": metrics_file})
    final_d.update(run_file)

    # final_d['captured_out'] = cout_file

    if error_entry:
        final_d["status"] = "FAILED"
        collection.replace_one({"_id": insert_id}, final_d, upsert=True)
        return

    # convert dates to isodates
    date_keys = ["stop_time", "heartbeat", "start_time"]
    for k in date_keys:
        final_d[k] = dateutil.parser.parse(final_d[k])

    # setup mongo filestorage
    mongodb_config = seml.database.get_mongodb_config()
    db = seml.database.get_database(**mongodb_config)

    fs = gridfs.GridFS(db)

    # add artifacts
    if True:
        new_artificats = []
        for a in final_d["artifacts"]:
            a_fp = get_fp(a)

            with open(a_fp, "rb") as f:
                db_filename = "artifact://{}/{}/{}".format(basedir, insert_id, a)

                file_id = fs.put(
                    f, filename=db_filename, metadata=None, content_type=None
                )

                if state.verbose:
                    print("artifact: ", file_id)

            new_artificats.append({"name": a, "file_id": file_id})

        final_d["artifacts"] = new_artificats

    # add source files
    new_sources = []
    for a in final_d["experiment"]["sources"]:
        name = a[0]
        a_fp = basedir + "/" + a[1]
        db_filename = project_dir + "/" + basedir + "/" + name

        with open(a_fp, "rb") as f:
            file_id = fs.put(f, filename=db_filename)

        new_sources.append([name, file_id])

    final_d["experiment"]["sources"] = new_sources

    collection.replace_one({"_id": insert_id}, final_d, upsert=True)
