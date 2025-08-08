from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from product.models import Product
from decimal import Decimal
import random
import json

User = get_user_model()


class Command(BaseCommand):
    help = 'Add 10 fake dental products to the database'

    def handle(self, *args, **options):
        # Get the first user or create a default one
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.WARNING('No users found. Please create a user first.'))
            return

        fake_products = [
            {
                'name': 'ProMax Dental X-Ray System',
                'sku': 'PMX-2024-001',
                'category': 'equipment',
                'brand': 'DentalTech Pro',
                'manufacturer': 'ProMax Medical Systems',
                'short_description': 'Advanced digital X-ray system with high-resolution imaging',
                'long_description': 'The ProMax Dental X-Ray System delivers exceptional image quality with minimal radiation exposure. Features include digital sensor technology, instant image processing, and seamless integration with practice management software.',
                'features': 'High-resolution digital imaging\nLow radiation exposure\nInstant image processing\nPACS integration\n5-year warranty',
                'specifications': {
                    'voltage': '60-70 kV',
                    'current': '7 mA',
                    'exposure_time': '0.02-3.2 seconds',
                    'focal_spot': '0.7 mm',
                    'weight': '85 kg'
                },
                'price': Decimal('35999.99'),
                'cost': Decimal('28000.00'),
                'quantity_in_stock': 3,
                'weight': Decimal('85.000'),
                'dimensions': '120 x 80 x 200',
                'tags': 'x-ray,imaging,diagnostic,digital'
            },
            {
                'name': 'UltraClean Autoclave Sterilizer AS-500',
                'sku': 'UC-AS500-2024',
                'category': 'equipment',
                'brand': 'UltraClean',
                'manufacturer': 'SterilTech Industries',
                'short_description': 'High-capacity autoclave sterilizer for dental instruments',
                'long_description': 'The UltraClean AS-500 provides reliable sterilization with advanced safety features. Perfect for busy dental practices requiring quick turnaround times and consistent results.',
                'features': 'Class B sterilization\n23-liter capacity\nAutomatic door locking\nUSB data logging\nSelf-diagnostic system',
                'specifications': {
                    'capacity': '23 liters',
                    'cycles': 'Class B, Class N, Class S',
                    'temperature_range': '105-134°C',
                    'pressure': '2.1 bar',
                    'power': '2300W'
                },
                'price': Decimal('8999.99'),
                'cost': Decimal('6500.00'),
                'quantity_in_stock': 8,
                'weight': Decimal('55.500'),
                'dimensions': '60 x 45 x 45',
                'tags': 'sterilization,autoclave,infection control'
            },
            {
                'name': 'DentaPro Composite Filling Kit',
                'sku': 'DP-CFK-PRO',
                'category': 'materials',
                'brand': 'DentaPro',
                'manufacturer': 'DentaPro Materials Inc.',
                'short_description': 'Professional composite filling material kit with 8 shades',
                'long_description': 'Complete composite filling kit featuring nano-hybrid technology for superior aesthetics and durability. Includes 8 popular shades for perfect color matching.',
                'features': 'Nano-hybrid technology\n8 shade selection\nHigh polish retention\nLow shrinkage\nExcellent handling',
                'specifications': {
                    'shades': 'A1, A2, A3, A3.5, B1, B2, C2, D3',
                    'particle_size': '0.02-2.5 μm',
                    'filler_content': '78.5% by weight',
                    'curing_time': '20 seconds',
                    'compressive_strength': '380 MPa'
                },
                'price': Decimal('299.99'),
                'cost': Decimal('180.00'),
                'quantity_in_stock': 45,
                'weight': Decimal('0.850'),
                'dimensions': '25 x 20 x 8',
                'tags': 'composite,filling,restoration,aesthetic'
            },
            {
                'name': 'ErgoComfort Dental Chair EC-3000',
                'sku': 'EC-3000-LUX',
                'category': 'equipment',
                'brand': 'ErgoComfort',
                'manufacturer': 'Dental Furniture Solutions',
                'short_description': 'Ergonomic dental chair with memory foam and LED surgical light',
                'long_description': 'The ErgoComfort EC-3000 combines patient comfort with practitioner efficiency. Features programmable positions, integrated LED surgical light, and premium memory foam upholstery.',
                'features': 'Memory foam cushioning\n4 programmable positions\nIntegrated LED light\nFoot control operation\nAuto-return function',
                'specifications': {
                    'weight_capacity': '180 kg',
                    'height_range': '350-800 mm',
                    'backrest_angle': '0-80 degrees',
                    'power_supply': '220-240V AC',
                    'led_intensity': '8,000-35,000 lux'
                },
                'price': Decimal('15999.99'),
                'cost': Decimal('11000.00'),
                'quantity_in_stock': 2,
                'weight': Decimal('120.000'),
                'dimensions': '180 x 85 x 120',
                'tags': 'chair,furniture,ergonomic,LED'
            },
            {
                'name': 'QuickSet Impression Material - Heavy Body',
                'sku': 'QS-IMP-HB50',
                'category': 'materials',
                'brand': 'QuickSet',
                'manufacturer': 'Precision Dental Materials',
                'short_description': 'Fast-setting heavy body impression material, 50ml cartridges',
                'long_description': 'QuickSet Heavy Body impression material offers exceptional dimensional stability and tear resistance. Ideal for crown and bridge impressions with minimal distortion.',
                'features': 'Fast setting time\nHigh tear resistance\nExcellent flow\nDimensional stability\nPleasant mint flavor',
                'specifications': {
                    'working_time': '2 minutes',
                    'setting_time': '3.5 minutes',
                    'shore_a_hardness': '60',
                    'dimensional_change': '<0.1%',
                    'tear_strength': '3.5 N/mm'
                },
                'price': Decimal('89.99'),
                'cost': Decimal('55.00'),
                'quantity_in_stock': 120,
                'weight': Decimal('0.450'),
                'dimensions': '15 x 10 x 8',
                'tags': 'impression,material,heavy body,prosthodontics'
            },
            {
                'name': 'TurboVac Suction System TS-800',
                'sku': 'TV-TS800-24',
                'category': 'equipment',
                'brand': 'TurboVac',
                'manufacturer': 'Vacuum Systems International',
                'short_description': 'High-performance dental suction system for 4 operatories',
                'long_description': 'The TurboVac TS-800 provides powerful, quiet suction for up to 4 operatories simultaneously. Features wet/dry separation and automatic drain system.',
                'features': 'Serves 4 operatories\nWet/dry separation\nAutomatic drain\nLow noise operation\nEnergy efficient motor',
                'specifications': {
                    'suction_power': '300 mbar',
                    'air_flow': '800 l/min',
                    'motor_power': '1.5 kW',
                    'noise_level': '62 dB',
                    'tank_capacity': '20 liters'
                },
                'price': Decimal('4599.99'),
                'cost': Decimal('3200.00'),
                'quantity_in_stock': 5,
                'weight': Decimal('45.000'),
                'dimensions': '60 x 50 x 90',
                'tags': 'suction,vacuum,equipment,operatory'
            },
            {
                'name': 'NiTi Rotary File System - Complete Set',
                'sku': 'NITI-RFS-25',
                'category': 'instruments',
                'brand': 'EndoPro',
                'manufacturer': 'Precision Endodontics Ltd.',
                'short_description': 'Complete set of 25 NiTi rotary files for endodontic procedures',
                'long_description': 'Premium nickel-titanium rotary file system designed for efficient root canal preparation. Heat-treated for enhanced flexibility and resistance to cyclic fatigue.',
                'features': 'Heat-treated NiTi alloy\nProgressive taper design\nEnhanced flexibility\nColor-coded system\nAutoclavable',
                'specifications': {
                    'sizes': '15-40',
                    'taper': '0.04-0.06',
                    'length': '21mm, 25mm, 31mm',
                    'speed_range': '250-350 rpm',
                    'torque': '1.5-3.0 Ncm'
                },
                'price': Decimal('599.99'),
                'cost': Decimal('420.00'),
                'quantity_in_stock': 25,
                'weight': Decimal('0.250'),
                'dimensions': '20 x 15 x 5',
                'tags': 'endodontic,rotary,files,NiTi,instruments'
            },
            {
                'name': 'DentaView Intraoral Camera System',
                'sku': 'DV-CAM-4K',
                'category': 'equipment',
                'brand': 'DentaView',
                'manufacturer': 'Digital Dental Imaging Corp.',
                'short_description': '4K intraoral camera with wireless connectivity',
                'long_description': 'State-of-the-art 4K intraoral camera system with wireless image transfer and auto-focus technology. Perfect for patient education and documentation.',
                'features': '4K resolution\nWireless connectivity\nAuto-focus\nFreeze frame capture\nUSB-C charging',
                'specifications': {
                    'resolution': '3840 x 2160 (4K)',
                    'sensor': '1/2.5" CMOS',
                    'field_of_view': '105 degrees',
                    'depth_of_field': '5-50mm',
                    'battery_life': '4 hours continuous'
                },
                'price': Decimal('2499.99'),
                'cost': Decimal('1800.00'),
                'quantity_in_stock': 12,
                'weight': Decimal('0.320'),
                'dimensions': '25 x 5 x 5',
                'tags': 'camera,intraoral,imaging,4K,wireless'
            },
            {
                'name': 'ProWhite LED Whitening System',
                'sku': 'PW-LED-SYS',
                'category': 'equipment',
                'brand': 'ProWhite',
                'manufacturer': 'Cosmetic Dental Technologies',
                'short_description': 'Professional LED teeth whitening system with adjustable intensity',
                'long_description': 'The ProWhite LED system delivers professional whitening results with customizable treatment protocols. Features blue LED technology and ergonomic design.',
                'features': 'Blue LED technology\n3 intensity settings\nTimer function\nErgonomic design\nPortable carrying case',
                'specifications': {
                    'wavelength': '465-480 nm',
                    'power_output': '24W',
                    'timer_settings': '10, 15, 20 minutes',
                    'input_voltage': '100-240V AC',
                    'led_lifespan': '50,000 hours'
                },
                'price': Decimal('1899.99'),
                'cost': Decimal('1200.00'),
                'quantity_in_stock': 7,
                'weight': Decimal('2.500'),
                'dimensions': '35 x 25 x 15',
                'tags': 'whitening,LED,cosmetic,bleaching'
            },
            {
                'name': 'SafeGuard Nitrile Gloves - Box of 200',
                'sku': 'SG-NIT-L200',
                'category': 'supplies',
                'brand': 'SafeGuard',
                'manufacturer': 'Medical Safety Products Inc.',
                'short_description': 'Powder-free nitrile examination gloves, size Large',
                'long_description': 'Premium quality powder-free nitrile gloves offering superior protection and tactile sensitivity. Latex-free and suitable for sensitive skin.',
                'features': 'Powder-free\nLatex-free\nTextured fingertips\nAmbidextrous\nBeaded cuff',
                'specifications': {
                    'material': '100% Nitrile',
                    'thickness': '4 mil',
                    'length': '240mm',
                    'color': 'Blue',
                    'standards': 'FDA 510(k), CE marked'
                },
                'price': Decimal('29.99'),
                'cost': Decimal('18.00'),
                'discount_percentage': Decimal('10.00'),
                'quantity_in_stock': 500,
                'weight': Decimal('1.200'),
                'dimensions': '24 x 12 x 6',
                'tags': 'gloves,nitrile,PPE,supplies,disposable'
            }
        ]

        created_count = 0
        for product_data in fake_products:
            try:
                product, created = Product.objects.get_or_create(
                    sku=product_data['sku'],
                    defaults={
                        **product_data,
                        'status': 'active',
                        'is_featured': random.choice([True, False]),
                        'created_by': user,
                        'specifications': json.dumps(product_data['specifications']) if isinstance(product_data['specifications'], dict) else product_data['specifications']
                    }
                )
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f'Created product: {product.name}'))
                else:
                    self.stdout.write(self.style.WARNING(f'Product already exists: {product.name}'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating product {product_data["name"]}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {created_count} products'))