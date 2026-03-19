#!/bin/bash

# Script retrieved from the Galaxy Project's KUI GitHub repository
# https://github.com/galaxyproject/kui/blob/091fbf678c84085a7689be0120c722042812e8a7/kui.sh

# Query a Galaxy database to extract values for populating the Key Usage Indicators dashboard, available at gxy.io/kui.

# Before running this script, update the varaibles at top as needed.
# Usage: ./kui.sh [YYYY] [MM]

##############################################################################
# To be able to run the script, you need to authenticate with Google Cloud:  #
# gcloud init                                                                #
# gcloud config set project anvil-cost-modeling                              #
# gcloud auth application-default login                                      #
##############################################################################

# Set the BigQuery project ID, dataset, and table name
PROJECT_ID="anvil-cost-modeling"
DATASET="kui"
USERS_TABLE="users-eu"
JOBS_TABLE="jobs-eu"
USAGE_TABLE="usage-eu"

galaxy_server="https://usegalaxy.eu"
#export PGDATABASE=$PGHOST
#export PATH=/home/afgane/google-cloud-sdk/bin/:$PATH


# If month and years parameters are passed, use them, otherwise use previous month
if [ -z "$2" ]
then
    year=`date -d "last month" +"%Y"`
    month=`date -d "last month" +"%m"`
else
    year=$1
    month=$2
fi
# Add one month to $month because that's what some gxadmin queries expect.
next_month=$(date -d "${year}${month}01+1 month" +%Y-%m-%d)


start_time=`date +%s`
echo "[`date`] ----------------------------------------------------------------------"
echo "[`date`] -- Working on data for $year-$month."


# Get user data
echo "[`date`] -- Getting user data."
total_registered=$(gxadmin query users-total "$next_month" | awk "/[0-9]+$/ { print \$1 }")
echo "[`date`] --- Total registered users: $total_registered"

new_registrations=$(gxadmin query monthly-users-registered --year="$year" --month="$month" | awk "/$year-$month/ { print \$3 }")
echo "[`date`] --- New user registrations: $new_registrations"

engaged=$(gxadmin query monthly-users-active --year=$year --month=$month | awk "/$year-$month/ { print \$3 }")
echo "[`date`] --- Engaged users: $engaged"

engaged_day_plus=$(gxadmin query users-engaged-multiday $year-$month | awk "/$year-$month/ { print \$3 }")
echo "[`date`] --- Engaged users more than a day: $engaged_day_plus"

new_engaged_day_plus=$(gxadmin query users-engaged-multiday $year-$month --new_only | awk "/$year-$month/ { print \$3 }")
echo "[`date`] --- New engaged users more than a day: $new_engaged_day_plus"


# Check if entries for the given month already exist in BQ
check_users_query="SELECT COUNT(*) FROM \`$PROJECT_ID\`.$DATASET.\`$USERS_TABLE\` WHERE month='$year-$month-01'"
# echo "[`date`] -- $check_users_query"
users_entry_exists=$(bq query --use_legacy_sql=false --project_id="$PROJECT_ID" --format=csv "$check_users_query" | awk '/[0-9]+$/ { print $1 }')
echo "[`date`] -- Users data for $year-$month exists in BQ: $users_entry_exists"


# If entry for the given month does not exist, insert data. Otherwise, update the values.
if [ "$users_entry_exists" -eq 0 ]; then
    # Build an INSERT query and run it
    users_insert_query="INSERT INTO \`$PROJECT_ID\`.$DATASET.\`$USERS_TABLE\` (month, total_registered, new_registrations, engaged, engaged_day_plus, new_engaged_day_plus) VALUES ('$year-$month-01', $total_registered, $new_registrations, $engaged, $engaged_day_plus, $new_engaged_day_plus)"
    echo "[`date`] -- Inserting new user vales using: $users_insert_query"
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" "$users_insert_query"
else
    # Build and UPDATE query and run it
    users_update_query="UPDATE \`$PROJECT_ID\`.$DATASET.\`$USERS_TABLE\` SET total_registered=$total_registered, new_registrations=$new_registrations, engaged=$engaged, engaged_day_plus=$engaged_day_plus, new_engaged_day_plus=$new_engaged_day_plus WHERE month='$year-$month-01'"
    echo "[`date`] -- Updating users values for $year-$month using: $users_update_query"
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" "$users_update_query"
fi



# Get job data
echo "[`date`] -- Getting job data."
total_jobs=$(gxadmin query total-jobs $next_month --no_state | awk '/[0-9]+$/ { print $1 }')
echo "[`date`] --- Total jobs: $total_jobs"

month_jobs=$(gxadmin query monthly-jobs --year=$year --month=$month | awk "/$year-$month/ { print \$3 }")
echo "[`date`] --- Jobs in $year-$month: $month_jobs"

by_new_users=$(gxadmin query monthly-jobs-by-new-users $year-$month --no_state | awk "/$year-$month/ { print \$3 }")
echo "[`date`] --- Jobs by new users: $by_new_users"

by_new_users_engaged_day_plus=$(gxadmin query monthly-jobs-by-new-multiday-users $year-$month | awk "/$year-$month/ { print \$3 }")
echo "[`date`] --- Jobs by new users engaged more than a day: $by_new_users_engaged_day_plus"

errored=$(gxadmin query monthly-jobs --year=$year --month=$month --state='error' | awk "/$year-$month/ { print \$3 }")
echo "[`date`] --- Errored jobs: $errored"

errored_by_new_users=$(gxadmin query monthly-jobs-by-new-users $year-$month --state='error' | awk "/$year-$month/ { print \$5 }")
echo "[`date`] --- Errored jobs by new users: $errored_by_new_users"


# Check if entries for the given month already exist in BQ
check_jobs_query="SELECT COUNT(*) FROM \`$PROJECT_ID\`.$DATASET.\`$JOBS_TABLE\` WHERE month='$year-$month-01'"
# echo "[`date`] -- $check_jobs_query"
jobs_entry_exists=$(bq query --use_legacy_sql=false --project_id="$PROJECT_ID" --format=csv "$check_jobs_query" | awk '/[0-9]+$/ { print $1 }')
echo "[`date`] -- Jobs data for $year-$month exists in BQ: $jobs_entry_exists"

# If entry for the given month does not exist, insert data. Otherwise, update the values.
if [ "$jobs_entry_exists" -eq 0 ]; then
    # Build an INSERT query and run it
    jobs_query="INSERT INTO \`$PROJECT_ID\`.$DATASET.\`$JOBS_TABLE\` (month, total_jobs, month_jobs, by_new_users, by_new_users_engaged_day_plus, errored, errored_by_new_users) VALUES ('$year-$month-01', $total_jobs, $month_jobs, $by_new_users, $by_new_users_engaged_day_plus, $errored, $errored_by_new_users)"
    echo "[`date`] -- Inserting new jobs vales using: $jobs_query"
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" "$jobs_query"
else
    # Build and UPDATE query and run it
    jobs_update_query="UPDATE \`$PROJECT_ID\`.$DATASET.\`$JOBS_TABLE\` SET total_jobs=$total_jobs, month_jobs=$month_jobs, by_new_users=$by_new_users, by_new_users_engaged_day_plus=$by_new_users_engaged_day_plus, errored=$errored, errored_by_new_users=$errored_by_new_users WHERE month='$year-$month-01'"
    echo "[`date`] -- Updating jobs values for $year-$month using: $jobs_update_query"
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" "$jobs_update_query"
fi



# Get usage data
echo "[`date`] -- Getting usage data."
num_histories=$(gxadmin query history-count $next_month | awk '/[0-9]+$/ { print $1 }')
echo "[`date`] --- Histories: $num_histories"

num_datasets=$(gxadmin query dataset-count $next_month | awk '/[0-9]+$/ { print $1 }')
echo "[`date`] --- Datasets: $num_datasets"

num_workflows=$(gxadmin query workflow-count $next_month | awk '/[0-9]+$/ { print $1 }')
echo "[`date`] --- Workflows: $num_workflows"

num_workflow_invocations=$(gxadmin query workflow-invocation-count $next_month | awk '/[0-9]+$/ { print $1 }')
echo "[`date`] --- Workflow invocations: $num_workflow_invocations"

num_tool_installs=$(curl -sS "$galaxy_server"/api/tools?in_panel=false | jq '[.[] | select(has("id") and .hidden == "")] | length')
echo "[`date`] --- Tool installs: $num_tool_installs"

# Check if entries for the given month already exist in BQ
check_usage_query="SELECT COUNT(*) FROM \`$PROJECT_ID\`.$DATASET.\`$USAGE_TABLE\` WHERE month='$year-$month-01'"
# echo "[`date`] -- $check_usage_query"
usage_entry_exists=$(bq query --use_legacy_sql=false --project_id="$PROJECT_ID" --format=csv "$check_usage_query" | awk '/[0-9]+$/ { print $1 }')
echo "[`date`] -- Usage data for $year-$month exists in BQ: $check_usage_query"

# If entry for the given month does not exist, insert data. Otherwise, update the values.
if [ "$usage_entry_exists" -eq 0 ]; then
    # Build an INSERT query and run it
    usage_insert_query="INSERT INTO \`$PROJECT_ID\`.$DATASET.\`$USAGE_TABLE\` (month, total_histories, total_datasets, total_workflows, total_workflow_invocations, tool_installs) VALUES ('$year-$month-01', $num_histories, $num_datasets, $num_workflows, $num_workflow_invocations, $num_tool_installs)"
    echo "[`date`] -- Inserting new usage vales using: $usage_insert_query"
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" "$usage_insert_query"
else
    # Build and UPDATE query and run it
    usage_update_query="UPDATE \`$PROJECT_ID\`.$DATASET.\`$USAGE_TABLE\` SET total_histories=$num_histories, total_datasets=$num_datasets, total_workflows=$num_workflows, total_workflow_invocations=$num_workflow_invocations, tool_installs=$num_tool_installs WHERE month='$year-$month-01'"
    echo "[`date`] -- Updating usage values for $year-$month using: $usage_update_query"
    bq query --use_legacy_sql=false --project_id="$PROJECT_ID" "$usage_update_query"
fi


endtime=`date +%s`
echo "[`date`] -- Done in $((endtime-start_time)) seconds."
