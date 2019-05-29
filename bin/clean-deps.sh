#!/bin/bash

for repo__version in $(ansible-galaxy list | awk '{gsub(", ", "\t"); print $2"__"$3}'); do
	vers="$(echo "$repo__version" | sed 's/.*__//g')"
	repo="$(echo "$repo__version" | sed 's/__.*//g')"

	# Ignore these, not proper ones.
	if [[ "$vers" != "(unkonwn" ]]; then
		results="$(grep "$repo" -A2 requirements.yaml)"
		ec=$?

		# Not under git's control
		if (( ec == 0 )); then
			expected_version=$(echo "$results" | grep version | sed 's/.*version: //g')

			if [[ "$expected_version" != "master" ]]; then
				if [[ "$vers" != "$expected_version" ]]; then
					echo "Removing $repo: $vers != $expected_version";
					ansible-galaxy remove "$repo"
				fi
			fi
		fi
	fi
done
