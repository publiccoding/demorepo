
default['multirecipe']['tobeexecuted'] = true 
if node['platform'] == 'ubuntu' 
    default['multirecipe']['package_name'] = 'apache2'
else node['platform'] == 'redhat'
    default['multirecipe']['package_name'] = 'httpd'
end

default['multirecipe']['multiple'] = ["tree","git","nano"]
