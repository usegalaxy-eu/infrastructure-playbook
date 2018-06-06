#!/usr/bin/env python
import sys

tags = {}
data = {}

tags_done = False
block = []
block_name = None

def name_map(name):
	if 'Connection information for squid' in name:
		return 'conn'
	elif 'Cache information for squid' in name:
		return 'cache'
	elif 'Median Service Times' in name:
		return 'timing'
	elif 'Resource usage for squid' in name:
		return 'usage'
	elif 'Memory accounted for' in name:
		return 'mem'
	elif 'File descriptor usage for squid' in name:
		return 'file'
	elif 'Internal Data Structures' in name:
		return 'ids'

def parse_line(block, line):
	if block == 'conn':
		line = line.strip()
		if 'Number of' in line:
			key, val = line.split('\t')
			key = key[len('Number of '):-1].lower().replace(' ', '_')
			yield key, val
		elif 'Request failure ratio' in line:
			key = 'failure_ratio'
			val = line.split('\t')[1].strip()
			yield key, val
		elif 'Average HTTP requests per minute since start' in line:
			key = 'avg_http_per_minute'
			val = line.split('\t')[1].strip()
			yield key, val
		elif 'Average ICP messages per minute since start' in line:
			key = 'avg_icp_per_minute'
			val = line.split('\t')[1].strip()
			yield key, val
		elif 'Select loop called' in line:
			key = 'select_loop_count'
			kvv = line[len('Select loop called: '):].split(' ')
			yield key, kvv[0]
			key = 'select_loop_avg'
			yield key, kvv[2]
	elif block == 'cache':
		kv = [x.strip() for x in line.split(':')]
		if 'Hits as % of all requests' in line:
			key = 'hits_perc_reqs'
			vals = ' '.join(kv[1:]).split(' ')
			val = vals[1].strip('%,')
			yield key + '_5m', val
			val = vals[3].strip('%,')
			yield key + '_60m', val
		elif 'Hits as % of bytes sent' in line:
			key = 'hits_perc_bytes'
			vals = ' '.join(kv[1:]).split(' ')
			val = vals[1].strip('%,')
			yield key + '_5m', val
			val = vals[3].strip('%,')
			yield key + '_60m', val
		elif 'Memory hits as % of hit requests' in line:
			key = 'mem_hits_perc_req'
			vals = ' '.join(kv[1:]).split(' ')
			val = vals[1].strip('%,')
			yield key + '_5m', val
			val = vals[3].strip('%,')
			yield key + '_60m', val
		elif 'Disk hits as % of hit requests' in line:
			key = 'disk_hits_perc_req'
			vals = ' '.join(kv[1:]).split(' ')
			val = vals[1].strip('%,')
			yield key + '_5m', val
			val = vals[3].strip('%,')
			yield key + '_60m', val
		elif 'Storage Swap size' in line:
			key = 'stor_swap_size'
			yield key, kv[1].strip(' KB')
		elif 'Storage Swap capacity' in line:
			key = 'stor_swap_cap'
			val = kv[1].split(' ')
			yield key + '_used', val[0].strip('%')
			yield key + '_free', val[2].strip('%')
		elif 'Storage Mem size' in line:
			key = 'stor_mem_size'
			yield key, kv[1].strip(' KB')
		elif 'Storage Mem capacity' in line:
			key = 'stor_mem_cap'
			val = kv[1].split()
			yield key + '_used', val[0].strip('%')
			yield key + '_free', val[2].strip('%')
		elif 'Mean Object Size' in line:
			key = 'mean_obj_size'
			yield key, kv[1].strip(' KB')
		elif 'Requests given to unlinkd' in line:
			key = 'request_to_unlink'
			yield key, kv[1]
	elif block == 'timing':
		if 'HTTP Requests (All)' in line:
			key = 'http_reqs'
		elif 'Cache Misses' in line:
			key = 'cache_miss'
		elif 'Cache Hits' in line:
			key = 'cache_hits'
		elif 'Near Hits' in line:
			key = 'near_hits'
		elif 'Not-Modified Replies' in line:
			key = 'not_modified'
		elif 'DNS Lookups' in line:
			key = 'dns_queries'
		elif 'ICP Queries' in line:
			key = 'icp_queries'
		kvv = [x.strip() for x in line.split(':')]
		vv = kvv[1].split()
		yield key + '_5m', vv[0]
		yield key + '_60m', vv[1]
	elif block == 'usage':
		kv = [x.strip() for x in line.split(':')]
		val = kv[1].strip(' seconds').strip(' KB').strip('%')
		if 'UP Time' in line:
			key = 'uptime'
		elif 'CPU Time' in line:
			key = 'cputime'
		elif 'CPU Usage' in line:
			key = 'cpu_usage'
		elif 'CPU Usage, 5 minute avg' in line:
			key = 'cpu_usage_5m'
		elif 'CPU Usage, 60 minute avg' in line:
			key = 'cpu_usage_60m'
		elif 'Maximum Resident Size' in line:
			key = 'max_rss'
		elif 'Page faults with physical i/o' in line:
			key = 'page_faults'
		yield key, val
	elif block == 'mem':
		kv = [x.strip() for x in line.split(':')]
		val = kv[1].strip(' seconds').strip(' KB').strip('%')
		if 'Total accounted' in line:
			key = 'total'
		elif 'memPoolAlloc calls' in line:
			key = 'memPoolAlloc_calls'
		elif 'memPoolFree calls' in line:
			key = 'memPoolFree_calls'
		yield key, val
	elif block == 'file':
		kv = [x.strip() for x in line.split(':')]
		val = kv[1].strip(' seconds').strip(' KB').strip('%')
		if 'Maximum number of file descriptors' in line:
			key = 'max_num_fd'
		elif 'Largest file desc currently in use' in line:
			key = 'largest_active_fd'
		elif 'Number of file desc currently in use' in line:
			key = 'num_fd'
		elif 'Files queued for open' in line:
			key = 'open_queue'
		elif 'Available number of file descriptors' in line:
			key = 'avail_fd'
		elif 'Reserved number of file descriptors' in line:
			key = 'reserved_fd'
		elif 'Store Disk files open' in line:
			key = 'store_disk_files_open'
		yield key, val
	elif block == 'ids':
		val = line.strip().split(' ')[0]
		if 'StoreEntries' in line:
			key = 'storeEnts'
		elif 'StoreEntries with MemObjects' in line:
			key = 'storeEnts_with_memObj'
		elif 'Hot Object Cache Items' in line:
			key = 'hot_obj_cache_items'
		elif 'on-disk objects' in line:
			key = 'on_disk_obj'
		yield key, val

for line in sys.stdin:
	if line.strip() == 'Connection information for squid:':
		tags_done = True

	if not tags_done:
		if 'Squid Object Cache:' in line:
			tags['version'] = line[line.index('Version') + len('Version '):].strip()
		if 'Service Name:' in line:
			tags['name'] = line[line.index('Service Name:') + len('Service Name:'):].strip()
		continue

	if line.startswith('\t'):
		block.extend(parse_line(block_name, line))
	else:
		if block_name:
			data[block_name] = block
		block_name = name_map(line.strip(':').strip())
		block = []

data[block_name] = block

for key, val in data.items():
	print(
		'squid.%s,%s %s' % (
		key,
		','.join(['%s=%s' % x for x in tags.items()]),
		','.join(['%s=%s' % x for x in val]),
	))
