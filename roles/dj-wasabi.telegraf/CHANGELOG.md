dj-wasabi.telegraf
------------------

Below an overview of all changes in the releases.

Version (Release date)

0.10.0 (2018-08-12)

  * Updating to telegraf 1.7.3
  * Fix Deprecation warnings #54
  * Changed 'include' to 'include_tasks' to remove deprecation warning #53 (By pull request: tjend (Thanks!))
  * Add option to remove extra plugin config files #52 (By pull request: tjend (Thanks!))
  * Plugins extra hash allow multiple inputs same type #50 (By pull request: tjend (Thanks!))
  * Using specific version for tests
  * Update minimum Ansible version to 2.4

0.9.0 (2018-05-06)

  * plugins: be able to specify the filename of extra plugings #40 (By pull request: gaelL (Thanks!))
  * Fix markdown #41 (By pull request: Angristan (Thanks!))
  * Allow to override RedHat release version #43 (By pull request: tszym (Thanks!))
  * Improved comments, split up role, moved tags and added defaults #45 (By pull request: boxrick (Thanks!))
  * Fix Travis Tests #42
  * Convert the telegraf_plugins_extra varaible to a hash so that we can … #46 (By pull request: tjend (Thanks!))

0.8.0 (2017-10-30)

  * Updating to Molecule V2
  * Test if LSB codename exists before using it #35 (By pull request: tszym (Thanks!))
  * Remove useless packages on RedHat. fix #28 #36 (By pull request: tszym (Thanks!))
  * Fix extra plugins by file / Change apt source filename / Change tags by global_tags #37 (By pull request: aarnaud (Thanks!))
  * Use telegra_global_tags for oldest telegraf versions #38 (By pull request: tszym (Thanks!))

0.7.0 (2017-02-23)

  * Replace action by modules #26 (By pull request: tszym (Thanks!))
  * Use yum repository to install telegraf on RedHat #25 (By pull request: tszym (Thanks!))
  * Remove for-loop in extra-plugin template #24 (By pull request: emersondispatch (Thanks!))
  * Update Debian.yml #23 (By pull request: zend0 (Thanks!))
  * extra plugins tags #21 (By pull request: oboukili (Thanks!))
  * Input tags support #20 (By pull request: szibis (Thanks!))
  * Fix telegraf confguration permissions #19 (By pull request: szibis (Thanks!))

0.6.0 (2017-01-02)

  * Fix the Influxdb repo for "hybrid" debian distros (like "jessie/sid") #9 (By pull request: Ismael (Thanks!))
  * Do "become" for the steps that require root access on Debian #10 (By pull request: Ismael (Thanks!))
  * Fix the Influxdb repo for "hybrid" debian distros (like "jessie/sid") #11 (By pull request: Ismael (Thanks!))
  * Removed imports #12
  * Fixing molecule #15
  * set telegraf hostname in defaults. #13 (By pull request: romainbureau (Thanks!))
  * use version_compare filter … #14 (By pull request: lhoss (Thanks!))
  * support missing agent settings upto telegraf v1.1 #16 (By pull request: lhoss (Thanks!))
  * update the README with the latest v0.13 - v1.1 agent settings #17 (By pull request: lhoss (Thanks!))

0.5.1 (2016-08-24)

  * fixed issue with ansible not getting the package #6 (By pull request: thecodeassassin (Thanks!))

0.5.0 (2016-07-17)

  * Removed Test Kitchen tests
  * Added Molecule tests and travis make use of them
  * Updated default version to 1.0.0 beta2
  * Feature/add extra plugins to telegrafd folder #5 (By pull request: stvnwrgs (Thanks!))

0.4.0 (2016-02-05)

  * Fixed test for test-kitchen
  * Added travis-ci test for testing default installation when PR is made
  * Fixed Download url for Debian
  * Removed default entry for telegraf_plugins_extra

0.3.0 (2016-01-13)

  * Made it work with telegraf 0.10.0
  * Default installation: 0.10.0

0.2.0 (2015-11-14)

  * Fixed kitchen test setup
  * Adding "net" to the telegraf_plugins_default property
  * Update etc-opt-telegraf-telegraf.conf.j2 #2 (By pull request: aferrari-technisys (Thanks!))
  * Improvement and upgrade for v0.2.0 of telegraf #1 (By pull request: aferrari-technisys (Thanks!))

0.1.0 (2015-09-23)

  * Updated `telegraf_agent_version` to 0.1.9
  * Added restart when package is changed (When updated for example)
  * Added several plugin options:
    * pass
    * drop
    * tagpass
    * tagdrop
    * interval
  * Updated documentation
  

0.0.2 (2015-09-20)

  * Updated README dus to missing colon
  * Forgot to update the meta file
  * Added Changelog file

0.0.1 (2015-09-20)

  * Initial release
