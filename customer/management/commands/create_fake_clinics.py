from django.core.management.base import BaseCommand
from customer.models import Customer
import random
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Creates 20 fake medical clinic customers'

    def handle(self, *args, **kwargs):
        # Medical clinic data
        clinic_types = [
            "Family Practice", "Pediatric Clinic", "Urgent Care", "Medical Center",
            "Health Clinic", "Wellness Center", "Medical Group", "Healthcare",
            "Clinic", "Medical Associates", "Health Services", "Care Center"
        ]
        
        clinic_names = [
            ("Sunrise", "Dr. Emily Johnson"),
            ("Valley View", "Dr. Michael Chen"),
            ("Riverside", "Dr. Sarah Williams"),
            ("Mountain", "Dr. David Martinez"),
            ("Lakeside", "Dr. Jennifer Brown"),
            ("Westside", "Dr. Robert Davis"),
            ("Eastside", "Dr. Lisa Anderson"),
            ("Central", "Dr. James Wilson"),
            ("North Shore", "Dr. Maria Garcia"),
            ("South Bay", "Dr. William Lee"),
            ("Harbor", "Dr. Patricia Taylor"),
            ("Hillcrest", "Dr. Christopher Moore"),
            ("Parkview", "Dr. Amanda Jackson"),
            ("Greenwood", "Dr. Daniel White"),
            ("Oakwood", "Dr. Michelle Harris"),
            ("Pine Ridge", "Dr. Kevin Thompson"),
            ("Cedar Grove", "Dr. Nancy Clark"),
            ("Maple", "Dr. Steven Lewis"),
            ("Willow Creek", "Dr. Karen Robinson"),
            ("Springfield", "Dr. Brian Walker")
        ]
        
        streets = [
            "Main Street", "Oak Avenue", "Elm Street", "First Avenue",
            "Second Street", "Park Boulevard", "Washington Avenue", "Lincoln Road",
            "Jefferson Street", "Madison Avenue", "Franklin Boulevard", "Roosevelt Way",
            "Kennedy Drive", "Martin Luther King Jr. Way", "Broadway", "Market Street",
            "University Avenue", "College Street", "Hospital Drive", "Medical Plaza"
        ]
        
        cities = [
            ("Seattle", "WA", "98101"),
            ("Bellevue", "WA", "98004"),
            ("Tacoma", "WA", "98402"),
            ("Spokane", "WA", "99201"),
            ("Vancouver", "WA", "98660"),
            ("Everett", "WA", "98201"),
            ("Kent", "WA", "98032"),
            ("Renton", "WA", "98055"),
            ("Federal Way", "WA", "98003"),
            ("Yakima", "WA", "98901")
        ]
        
        # Clear existing customers (optional)
        self.stdout.write('Creating fake medical clinic customers...')
        
        created_count = 0
        
        for i, (clinic_prefix, doctor_name) in enumerate(clinic_names):
            clinic_type = random.choice(clinic_types)
            company_name = f"{clinic_prefix} {clinic_type}"
            
            # Parse doctor name
            name_parts = doctor_name.replace("Dr. ", "").split()
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else "Smith"
            
            # Generate email
            email = f"contact@{clinic_prefix.lower().replace(' ', '')}{clinic_type.lower().replace(' ', '')}.com"
            
            # Generate phone
            area_code = random.choice(["206", "425", "253", "360", "509"])
            phone = f"+1{area_code}{random.randint(1000000, 9999999)}"
            
            # Generate address
            street_num = random.randint(100, 9999)
            street = random.choice(streets)
            suite = f"Suite {random.randint(100, 500)}" if random.random() > 0.5 else ""
            city, state, postal = random.choice(cities)
            
            # Random date in the last 2 years
            days_ago = random.randint(0, 730)
            date_joined = datetime.now() - timedelta(days=days_ago)
            
            # Create customer
            try:
                customer = Customer.objects.create(
                    company_name=company_name,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    address_line1=f"{street_num} {street}",
                    address_line2=suite,
                    city=city,
                    state=state,
                    postal_code=postal,
                    country="USA",
                    is_active=True,
                    notes=f"Medical clinic specializing in {clinic_type.lower()}. Primary contact: {doctor_name}."
                )
                customer.date_joined = date_joined
                customer.save()
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {company_name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating {company_name}: {str(e)}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {created_count} fake medical clinic customers!'))