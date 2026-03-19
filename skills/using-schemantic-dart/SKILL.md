---
name: using-schemantic-dart
description: Generates type-safe data classes and JSON schemas in Dart using the Schemantic library. Use when defining data models, implementing JSON serialization, or requiring runtime schema validation in Dart projects.
---

# Using Schemantic in Dart

Schemantic is a Dart library for defining strongly typed data classes that bind to reusable runtime JSON schemas. It is standard for the `genkit-dart` framework but works independently as well.

## Core Concepts

Always use `schemantic` when strongly typed JSON parsing or programmatic schema validation is required. 

- Annotate your abstract classes with `@Schema()`.
- Use the `$` prefix for abstract schema class names (e.g., `abstract class $User`).
- Always run `dart run build_runner build` to generate the `.g.dart` schema files.

## Usage Patterns

1. **Defining a schema:**

```dart
import 'package:schemantic/schemantic.dart';

part 'user.g.dart';  // Must match the filename

@Schema()
abstract class $User {
  String get name;
  
  @IntegerField(minimum: 0, description: 'Age of the user')
  int get age;
  
  $Address? get address; // Nullable = Optional in JSON
}

@Schema()
abstract class $Address {
  String get city;
  String get zipCode;
}
```

2. **Using the Generated Class:**

The builder creates a concrete class `User` (no `$`) with a factory constructor (`User.fromJson`) and a regular constructor.

```dart
// Instantiate using the generated class
final user = User(
  name: 'Alice', 
  age: 30,
  address: Address(city: 'New York', zipCode: '10001')
);

// Serialize to JSON Map
Map<String, dynamic> json = user.toJson();

// Parse from JSON Map
final parsedUser = User.fromJson(json);
// from raw data
final parsed = User.fromJson({'name': 'Bob', 'age': 25, 'address': {'city': 'Boston', 'zipCode': '20002'}});
```

3. **Accessing Schemas at Runtime:**

The generated data classes have a static `$schema` field (of type `SchemanticType<T>`) which can be used to pass the definition into functions or to extract the raw JSON schema.

```dart
// Access JSON schema
final schema = User.$schema.jsonSchema;
print(schema.toJson());

// Validate arbitrary JSON at runtime
final validationErrors = await schema.validate({'invalid': 'data'});
```

4. **Primitive & Dynamic Schemas**

Use `SchemanticType` factory methods for standalone schemas without classes:

```dart
// Primitives
final ageSchema = SchemanticType.integer(description: 'Age', minimum: 0);
final nameSchema = SchemanticType.string(minLength: 2);

// Collections
final listSchema = SchemanticType.list(SchemanticType.string());
final mapSchema = SchemanticType.map(
  SchemanticType.string(), 
  SchemanticType.integer()
);

// Special Types
final voidSchema = SchemanticType.voidSchema();
final anySchema = SchemanticType.dynamicSchema();
```

## Advanced Features

### Union Types (AnyOf)
To allow a field to accept multiple types, use `@AnyOf`.

```dart
@Schema()
abstract class $Poly {
  @AnyOf([int, String])
  Object? get id;
}
```

Schemantic generates a specific helper class (e.g., `PolyId`) to handle the values:

```dart
final poly1 = Poly(id: PolyId.int(123));
final poly2 = Poly(id: PolyId.string('abc'));
```

### Field Annotations

You can use specialized annotations for more validation boundaries:

```dart
@Schema()
abstract class $User {
  @IntegerField(
    name: 'years_old', // Change JSON key
    description: 'Age of the user',
    minimum: 0,
    defaultValue: 18,
  )
  int? get age;

  @StringField(
    minLength: 2,
    enumValues: ['user', 'admin'], 
  )
  String get role;
}
```

### Recursive Schemas
For recursive structures (like trees), set `useRefs: true` when generating the JSON schema representation.

```dart
@Schema()
abstract class $Node {
  String get id;
  List<$Node>? get children;
}
```
*Note*: `Node.$schema.jsonSchema(useRefs: true)` generates schemas with JSON Schema `$ref`.
