#!/bin/sh
set -eu

REPO_ROOT="/lab/homelab-llm"
HOST_HOME_ALIAS="/home/christopherbailey"

link_alias() {
    link_path="$1"
    target_path="$2"

    parent_dir=$(dirname "$link_path")
    if [ ! -d "$parent_dir" ]; then
        mkdir -p "$parent_dir"
    fi

    if [ -L "$link_path" ]; then
        current_target=$(readlink "$link_path")
        if [ "$current_target" = "$target_path" ]; then
            return 0
        fi
        rm -f "$link_path"
    elif [ -e "$link_path" ]; then
        return 0
    fi

    ln -s "$target_path" "$link_path"
}

create_repo_aliases() {
    link_alias "/homelab-llm" "$REPO_ROOT"
    link_alias "${HOST_HOME_ALIAS}/homelab-llm" "$REPO_ROOT"

    if [ ! -d "$REPO_ROOT" ]; then
        return 0
    fi

    for child in "$REPO_ROOT"/*; do
        [ -d "$child" ] || continue
        link_alias "/$(basename "$child")" "$child"
    done
}

create_repo_aliases

exec sudo -H -u user -- /app/entrypoint.sh "$@"
