require 'serverspec'

set :backend, :exec

describe file('/etc/chrony/chrony.conf') do
	it { should exist }
	it { should be_file }
end

describe service('chrony') do
  it { should be_running }
  it { should be_enabled }
end
