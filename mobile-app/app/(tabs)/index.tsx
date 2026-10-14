import { Text, View } from 'react-native';

export default function HomeScreen() {
  return (
    <View className="flex-1 items-center justify-center bg-green-700 px-6">
      <Text className="text-3xl font-bold text-white">
        Beverage Delivery
      </Text>

      <Text className="mt-3 text-center text-base text-white">
        Your favourite drinks, delivered to your door.
      </Text>
    </View>
  );
}
