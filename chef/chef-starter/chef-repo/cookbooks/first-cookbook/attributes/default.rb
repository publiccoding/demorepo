
if node['platform'] == 'ubuntu' 
    default['first-cookbook']['package_name'] = 'apache2'
else node['platform'] == 'redhat'
    default['first-cookbook']['package_name'] = 'httpd'
end
    
