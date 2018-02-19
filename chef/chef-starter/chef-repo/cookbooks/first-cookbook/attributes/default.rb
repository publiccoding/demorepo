# if node['platform'] == 'ubuntu' 
#     default['first-cookbook']['package_name'] = 'apache2'
# else node['platform'] == 'redhat'
#     default['first-cookbook']['package_name'] = 'httpd'
# end
default['first-cookbook']['tomcat_addition'] = ["tomcat7-docs","tomcat7-admin", "tomcat7-examples"]
default['first-cookbook']['username'] = 'admin'
default['first-cookbook']['password'] = 'pass'

# log 'message' do
#     message 'A message add to the log.'
#     level :info
#   end

# chef_handler 'name_of_handler' do
#     source '/path/to/handler/handler_name'
#     action :enable
#   end