provider "aws"{
        access_key = "AKIAJVAEVYXHHTZ5MYYA"
        secret_key = "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"
        region = "us-west-2"
            
}
resource "aws_instance" "myfirst"{
        ami = "ami-bf4193c7"
        instance_type = "t2.micro"

}
output "aws_instance_public_dns"{
        value = "${aws_instance.myfirst.public_dns}"


}

